#!/usr/bin/env python3

import argparse
import os
import re
import shutil
from pathlib import Path


VERSION_RE = re.compile(r"^(?P<name>.+)_v(?P<version>[^_]+)(?P<suffix>(?:_.*)?)\.lha$")
TOKEN_RE = re.compile(r"\d+|[A-Za-z]+")
NUMERIC_SUFFIX_RE = re.compile(r"^(?:_\d+(?:&\d+)*)$")


def parse_archive_name(filename):
    match = VERSION_RE.match(filename)
    if not match:
        return None
    return {
        "name": match.group("name"),
        "version": match.group("version"),
        "suffix": match.group("suffix"),
    }


def version_key(version):
    key = []
    for token in TOKEN_RE.findall(version.lower()):
        if token.isdigit():
            key.append((0, int(token)))
        else:
            key.append((1, token))
    return tuple(key)


def suffixes_compatible(current_suffix, candidate_suffix):
    if current_suffix == candidate_suffix:
        return True
    if not current_suffix and NUMERIC_SUFFIX_RE.match(candidate_suffix or ""):
        return True
    if not candidate_suffix and NUMERIC_SUFFIX_RE.match(current_suffix or ""):
        return True
    return False


def find_candidates(source_dir):
    candidates = {}
    by_basename = {}
    for path in source_dir.rglob("*.lha"):
        if "imported" in path.relative_to(source_dir).parts:
            continue
        parsed = parse_archive_name(path.name)
        if not parsed:
            continue
        candidates.setdefault(parsed["name"], []).append((version_key(parsed["version"]), parsed["suffix"], path))
        by_basename[path.name] = path
    for archive_name in candidates:
        candidates[archive_name].sort()
    return candidates, by_basename


def collect_current_archives(titles_dir):
    archives = []
    excluded_top_level_dirs = {"_generic", "_hacks", "_mt32"}
    for path in titles_dir.rglob("*.lha"):
        rel_parts = path.relative_to(titles_dir).parts
        if any(part == "retired" for part in rel_parts):
            continue
        if len(rel_parts) > 1 and rel_parts[1] in excluded_top_level_dirs:
            continue
        ignored_prefixes = {
            titles_dir / "manual-downloads",
        }
        if any(path.is_relative_to(prefix) for prefix in ignored_prefixes if prefix.exists()):
            continue
        parsed = parse_archive_name(path.name)
        if not parsed:
            continue
        archives.append((path, parsed))
    return archives


def retired_path_for_archive(archive_path):
    return archive_path.parent / "retired" / archive_path.name

def imported_path_for_source(source_dir, source_path):
    rel = source_path.relative_to(source_dir)
    return source_dir / "imported" / rel


def promote_archives(titles_dir, source_dir, apply=False):
    candidates, by_basename = find_candidates(source_dir)
    promoted = []
    missing = []
    skipped = []
    consumed_sources = set()

    for archive_path, parsed in collect_current_archives(titles_dir):
        current_version = version_key(parsed["version"])
        replacement = by_basename.get(archive_path.name)
        newer = [
            candidate_path
            for candidate_version, candidate_suffix, candidate_path in candidates.get(parsed["name"], [])
            if candidate_version > current_version and suffixes_compatible(parsed["suffix"], candidate_suffix)
        ]
        if newer:
            source_path = newer[-1]
        elif replacement:
            source_path = replacement
        else:
            missing.append(archive_path)
            continue
        dest_path = archive_path.with_name(source_path.name)
        retired_path = retired_path_for_archive(archive_path)

        promoted.append((archive_path, source_path, dest_path))
        consumed_sources.add(source_path)
        if apply:
            retired_path.parent.mkdir(parents=True, exist_ok=True)
            if retired_path.exists():
                os.remove(retired_path)
            shutil.move(str(archive_path), str(retired_path))
            shutil.copy2(source_path, dest_path)

    if apply:
        for source_path in sorted(consumed_sources):
            if not source_path.exists():
                continue
            imported_path = imported_path_for_source(source_dir, source_path)
            imported_path.parent.mkdir(parents=True, exist_ok=True)
            if imported_path.exists():
                os.remove(imported_path)
            shutil.move(str(source_path), str(imported_path))

    return promoted, missing, skipped


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", help="Directory to scan for newer .lha archives")
    parser.add_argument("--titles-dir", default="content/titles", help="Canonical titles directory")
    parser.add_argument("--apply", action="store_true", default=False, help="Copy newer archives into place and move replaced archives into a sibling retired/ directory")
    args = parser.parse_args()

    titles_dir = Path(args.titles_dir).resolve()
    source_dir = Path(args.source_dir).resolve()

    promoted, _, skipped = promote_archives(titles_dir, source_dir, apply=args.apply)

    action = "Promoted" if args.apply else "Would promote"
    for old_path, source_path, dest_path in promoted:
        print(f"old: {old_path.relative_to(titles_dir)}")
        print(f"new: {dest_path.relative_to(titles_dir)}")
        print()

    print(f"{action} {len(promoted)} archive(s)")

    if skipped:
        print()
        print(f"Skipped {len(skipped)} archive(s)")
        for old_path, dest_path, retired_path, reason in skipped:
            print(f"old: {old_path.relative_to(titles_dir)}")
            print(f"new: {dest_path.relative_to(titles_dir)}")
            print(f"retired: {retired_path.relative_to(titles_dir)}")
            print(f"why: {reason}")
            print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
