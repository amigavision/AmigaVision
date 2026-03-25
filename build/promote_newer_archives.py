#!/usr/bin/env python3

import argparse
import csv
import os
import re
import shutil
from collections import defaultdict
from pathlib import Path


VERSION_RE = re.compile(r"^(?P<name>.+)_v(?P<version>[^_]+)(?P<suffix>(?:_.*)?)\.lha$")
TOKEN_RE = re.compile(r"\d+|[A-Za-z]+")
NUMERIC_SUFFIX_RE = re.compile(r"^(?:_\d+(?:&\d+)*)$")
NONWHDL_TOP_LEVELS = {"game-notwhdl", "demo-notwhdl", "mags-notwhdl"}
CANONICAL_TOP_LEVEL_MAP = {
    "game": "game",
    "game-notwhdl": "game",
    "demo": "demo",
    "demo-notwhdl": "demo",
    "mags": "mags",
    "mags-notwhdl": "mags",
}


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


def normalized_title(value):
    value = value.replace("_", " ").replace("&", " and ")
    value = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", value)
    value = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    value = re.sub(r"(?<=[A-Za-z])(?=[0-9])", " ", value)
    value = re.sub(r"\s+", " ", value)
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def category_to_top_level(category, subcategory):
    if category == "Game":
        return "game"
    if category == "Demo" and subcategory == "Disk Magazine":
        return "mags"
    if category == "Demo":
        return "demo"
    return None


def load_csv_title_index(titles_dir):
    csv_path = Path(__file__).resolve().parents[1] / "data" / "db" / "titles.csv"
    index = defaultdict(set)
    if not csv_path.is_file():
        return index
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            top_level = category_to_top_level(row.get("category", ""), row.get("subcategory", ""))
            if not top_level:
                continue
            title = (row.get("title") or "").strip()
            if title:
                index[normalized_title(title)].add(top_level)
    return index


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


def canonicalize_top_level(top_level):
    return CANONICAL_TOP_LEVEL_MAP.get(top_level, top_level)


def top_level_for_archive(titles_dir, archive_path):
    rel = archive_path.relative_to(titles_dir)
    return rel.parts[0]


def variant_rank(suffix):
    suffix = suffix or ""
    tokens = [token.upper() for token in suffix.strip("_").split("_") if token]
    if "CD32" in tokens:
        return (0, len(tokens), suffix)
    if "AGA" in tokens:
        return (1, len(tokens), suffix)
    if not suffix or NUMERIC_SUFFIX_RE.match(suffix):
        return (2, len(tokens), suffix)
    if "SHAREWARE" in tokens:
        return (4, len(tokens), suffix)
    return (3, len(tokens), suffix)


def choose_preferred_new_candidate(entries):
    latest_version = max(version_key(parsed["version"]) for _, parsed in entries)
    latest_entries = [(path, parsed) for path, parsed in entries if version_key(parsed["version"]) == latest_version]
    return min(latest_entries, key=lambda item: variant_rank(item[1]["suffix"]))


def is_shareware_suffix(suffix):
    suffix = suffix or ""
    tokens = [token.upper() for token in suffix.strip("_").split("_") if token]
    return "SHAREWARE" in tokens


def select_additional_base_variants(entries, preferred_entry):
    preferred_path, preferred_parsed = preferred_entry
    preferred_rank = variant_rank(preferred_parsed["suffix"])[0]
    if preferred_rank not in (0, 1):
        return []

    preferred_version = version_key(preferred_parsed["version"])
    selected = []
    for path, parsed in entries:
        if path == preferred_path:
            continue
        if version_key(parsed["version"]) != preferred_version:
            continue
        rank = variant_rank(parsed["suffix"])[0]
        if rank != 2:
            continue
        selected.append((path, parsed))
    return selected


def determine_new_archive_top_level(titles_dir, archive_name, current_by_name, csv_title_index):
    existing_paths = current_by_name.get(archive_name, [])
    if existing_paths:
        canonical = canonicalize_top_level(top_level_for_archive(titles_dir, existing_paths[0]))
        if canonical:
            return canonical

    matches = csv_title_index.get(normalized_title(archive_name), set())
    for preferred in ("game", "demo", "mags"):
        if preferred in matches:
            return preferred

    return "game"


def promote_archives(titles_dir, source_dir, apply=False):
    candidates, by_basename = find_candidates(source_dir)
    csv_title_index = load_csv_title_index(titles_dir)
    promoted = []
    added = []
    missing = []
    skipped = []
    consumed_sources = set()
    current_archives = collect_current_archives(titles_dir)
    current_by_name = defaultdict(list)

    for archive_path, parsed in current_archives:
        current_by_name[parsed["name"]].append(archive_path)

    for archive_path, parsed in current_archives:
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

        top_level = canonicalize_top_level(top_level_for_archive(titles_dir, archive_path))
        dest_path = titles_dir / top_level / source_path.name
        retired_path = retired_path_for_archive(archive_path)

        promoted.append((archive_path, source_path, dest_path))
        consumed_sources.add(source_path)
        if apply:
            retired_path.parent.mkdir(parents=True, exist_ok=True)
            if retired_path.exists():
                os.remove(retired_path)
            shutil.move(str(archive_path), str(retired_path))
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, dest_path)

    unmatched_entries = []
    for path in sorted(by_basename.values()):
        if path in consumed_sources or not path.exists():
            continue
        parsed = parse_archive_name(path.name)
        if parsed is None:
            continue
        unmatched_entries.append((path, parsed))

    unmatched_by_name = defaultdict(list)
    for path, parsed in unmatched_entries:
        unmatched_by_name[parsed["name"]].append((path, parsed))

    review_sources = []
    for archive_name, entries in sorted(unmatched_by_name.items()):
        if current_by_name.get(archive_name):
            dropped = False
            for path, parsed in entries:
                if is_shareware_suffix(parsed["suffix"]):
                    consumed_sources.add(path)
                    dropped = True
                else:
                    review_sources.append(path)
            if dropped:
                continue
            continue

        preferred_entry = choose_preferred_new_candidate(entries)
        selected_entries = [preferred_entry, *select_additional_base_variants(entries, preferred_entry)]
        selected_paths = {path for path, _ in selected_entries}
        top_level = determine_new_archive_top_level(titles_dir, archive_name, current_by_name, csv_title_index)

        for source_path, parsed in selected_entries:
            dest_path = titles_dir / top_level / source_path.name
            if dest_path.exists():
                skipped.append((dest_path, source_path, dest_path, "destination already exists"))
                continue
            added.append((source_path, dest_path))
            consumed_sources.add(source_path)
            if apply:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, dest_path)

        review_sources.extend(path for path, _ in entries if path not in selected_paths)

    if apply:
        for source_path in sorted(consumed_sources):
            if not source_path.exists():
                continue
            imported_path = imported_path_for_source(source_dir, source_path)
            imported_path.parent.mkdir(parents=True, exist_ok=True)
            if imported_path.exists():
                os.remove(imported_path)
            shutil.move(str(source_path), str(imported_path))

    unmatched_sources = [
        path for path in sorted(review_sources)
        if path.exists()
    ]

    return promoted, added, missing, skipped, unmatched_sources


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", help="Directory to scan for newer .lha archives")
    parser.add_argument("--titles-dir", default=str(Path(os.getenv("AGSCONTENT", "content")) / "titles"), help="Canonical titles directory")
    parser.add_argument("--apply", action="store_true", default=False, help="Copy newer archives into place and move replaced archives into a sibling retired/ directory")
    args = parser.parse_args()

    titles_dir = Path(args.titles_dir).resolve()
    source_dir = Path(args.source_dir).resolve()

    promoted, added, _, skipped, unmatched_sources = promote_archives(titles_dir, source_dir, apply=args.apply)

    action = "Promoted" if args.apply else "Would promote"
    for old_path, source_path, dest_path in promoted:
        print(f"old: {old_path.relative_to(titles_dir)}")
        print(f"new: {dest_path.relative_to(titles_dir)}")
        print()

    print(f"{action} {len(promoted)} archive(s)")

    add_action = "Added" if args.apply else "Would add"
    for source_path, dest_path in added:
        print(f"add: {dest_path.relative_to(titles_dir)}")
        print(f"src: {source_path.relative_to(source_dir)}")
        print()

    print(f"{add_action} {len(added)} new archive(s)")

    if skipped:
        print()
        print(f"Skipped {len(skipped)} archive(s)")
        for old_path, source_path, dest_path, reason in skipped:
            try:
                old_rel = old_path.relative_to(titles_dir)
            except ValueError:
                old_rel = old_path
            print(f"old: {old_rel}")
            print(f"new: {dest_path.relative_to(titles_dir)}")
            print(f"src: {source_path.relative_to(source_dir)}")
            print(f"why: {reason}")
            print()

    if unmatched_sources:
        label = "Additional archive variants requiring manual review" if args.apply else "Archive variants that would still require manual review"
        print()
        print(f"{label}: {len(unmatched_sources)}")
        for source_path in unmatched_sources:
            print(source_path.relative_to(source_dir))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
