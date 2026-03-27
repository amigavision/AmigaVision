#!/usr/bin/env python3

import argparse
import csv
import importlib.util
import json
import os
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEST = Path("~/Developer/AmigaVision-Content").expanduser()
ALLOWED_TOP_LEVELS = {"demo", "game", "mags"}
VERSION_RE = re.compile(r"^(?P<name>.+)_v(?P<version>[^_]+)(?P<suffix>(?:_.*)?)\.lha$")
TOKEN_RE = re.compile(r"\d+|[A-Za-z]+")
NUMERIC_SUFFIX_RE = re.compile(r"^(?:_\d+(?:&\d+)*)$")


def load_pull_archives_module():
    module_path = Path(__file__).with_name("pull_archives.py")
    spec = importlib.util.spec_from_file_location("pull_archives", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_csv_archive_paths(csv_path: Path):
    rows = []
    seen = set()
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            archive_path = (row.get("archive_path") or "").strip()
            if not archive_path:
                continue
            top_level = Path(archive_path).parts[0]
            if top_level not in ALLOWED_TOP_LEVELS:
                continue
            if archive_path in seen:
                continue
            seen.add(archive_path)
            rows.append({
                "id": row["id"],
                "archive_path": archive_path,
                "basename": Path(archive_path).name,
                "top_level": top_level,
            })
    return rows


def write_tsv(path: Path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def load_json(path: Path, default):
    if not path.is_file():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
    for token in TOKEN_RE.findall((version or "").lower()):
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


def candidate_variant_rank(suffix):
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


def choose_version_fallback(row, candidates):
    requested = parse_archive_name(row["basename"])
    if requested is None:
        return []

    compatible = []
    requested_version_key = version_key(requested["version"])
    for remote_path in candidates:
        parsed = parse_archive_name(Path(remote_path).name)
        if parsed is None:
            continue
        if parsed["name"] != requested["name"]:
            continue
        if not suffixes_compatible(requested["suffix"], parsed["suffix"]):
            continue
        if version_key(parsed["version"]) < requested_version_key:
            continue
        compatible.append((remote_path, parsed))

    if not compatible:
        return []

    compatible.sort(key=lambda item: (version_key(item[1]["version"]),), reverse=True)
    latest_version = version_key(compatible[0][1]["version"])
    latest_entries = [item for item in compatible if version_key(item[1]["version"]) == latest_version]
    latest_entries.sort(key=lambda item: candidate_variant_rank(item[1]["suffix"]))
    best_remote_path, _ = latest_entries[0]
    return [best_remote_path]


def main():
    parser = argparse.ArgumentParser(
        description="Download canonical demo/game/mags archives listed in titles.csv using the same upstream source as make update."
    )
    parser.add_argument("--csv", default=str(ROOT / "data" / "db" / "titles.csv"), help="CSV file containing archive_path values")
    parser.add_argument("--dest", default=str(DEFAULT_DEST), help="Destination content root that will receive titles/demo, titles/game, and titles/mags")
    parser.add_argument("--reports-dir", default="", help="Optional directory for TSV/JSON reports; defaults to <dest>/.fetch-reports")
    parser.add_argument("--limit", type=int, default=0, help="Optional limit for how many unique archive_path entries to process")
    parser.add_argument("--dry-run", action="store_true", default=False, help="List/report actions without downloading files")
    args = parser.parse_args()

    pull_archives = load_pull_archives_module()

    csv_path = Path(args.csv).resolve()
    if not csv_path.is_file():
        raise SystemExit(f"CSV file not found: {csv_path}")

    dest_root = Path(args.dest).expanduser().resolve()
    titles_root = dest_root / "titles"
    reports_dir = Path(args.reports_dir).expanduser().resolve() if args.reports_dir else dest_root / ".fetch-reports"
    temp_dir = reports_dir / ".partial-downloads"
    state_path = reports_dir / "resume-state.json"
    titles_root.mkdir(parents=True, exist_ok=True)
    for name in sorted(ALLOWED_TOP_LEVELS):
        (titles_root / name).mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    rows = load_csv_archive_paths(csv_path)
    if args.limit > 0:
        rows = rows[:args.limit]

    sync_cmd_template = os.getenv("ARCHIVE_FETCH_SYNC_CMD", "").strip()
    login_cmd_template = os.getenv("ARCHIVE_FETCH_LOGIN_CMD", "").strip()
    list_cmd_template = os.getenv("ARCHIVE_FETCH_LIST_CMD", "").strip()
    get_cmd_template = os.getenv("ARCHIVE_FETCH_GET_CMD", "").strip()
    logout_cmd_template = os.getenv("ARCHIVE_FETCH_LOGOUT_CMD", "").strip()
    remote_ref = pull_archives.required_env("ARCHIVE_FETCH_REMOTE")

    if sync_cmd_template:
        raise SystemExit("ARCHIVE_FETCH_SYNC_CMD is not supported by this script; use list/get commands like make update.")

    missing_tools = [
        name
        for name, cmd in (
            ("ARCHIVE_FETCH_LOGIN_CMD", pull_archives.validate_template_binary(login_cmd_template) if login_cmd_template else ["optional"]),
            ("ARCHIVE_FETCH_LIST_CMD", pull_archives.validate_template_binary(list_cmd_template)),
            ("ARCHIVE_FETCH_GET_CMD", pull_archives.validate_template_binary(get_cmd_template)),
            ("ARCHIVE_FETCH_LOGOUT_CMD", pull_archives.validate_template_binary(logout_cmd_template) if logout_cmd_template else ["optional"]),
        )
        if not cmd
    ]
    if missing_tools:
        raise SystemExit("Archive fetch tool(s) not found from local env config: {}".format(", ".join(missing_tools)))

    logged_in = False
    try:
        if login_cmd_template:
            print("Connecting to archive source...")
            pull_archives.run(pull_archives.render_command(login_cmd_template, remote=remote_ref, path="", dest=str(titles_root)))
            logged_in = True

        print("Listing remote .lha archives...")
        result = pull_archives.run(
            pull_archives.render_command(list_cmd_template, remote=remote_ref, path="/", dest=str(titles_root)),
            capture_output=True,
        )
        remote_paths = pull_archives.parse_remote_lha_paths(result.stdout)
        if not remote_paths:
            raise SystemExit("No remote .lha archives found")

        (reports_dir / "remote_paths.txt").parent.mkdir(parents=True, exist_ok=True)
        (reports_dir / "remote_paths.txt").write_text("\n".join(remote_paths) + "\n", encoding="utf-8")

        by_basename = defaultdict(list)
        remote_version_candidates = list(remote_paths)
        for remote_path in remote_paths:
            by_basename[Path(remote_path).name].append(remote_path)

        downloaded = []
        downloaded_version_fallback = []
        skipped_existing = []
        missing_remote = []
        ambiguous = []
        ambiguous_rows = []
        failed = []
        resumed_state = load_json(state_path, {"completed_archive_paths": []})
        completed_archive_paths = set(resumed_state.get("completed_archive_paths", []))

        total = len(rows)
        for index, row in enumerate(rows, start=1):
            archive_path = row["archive_path"]
            basename = row["basename"]
            dest_path = titles_root / archive_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            if archive_path in completed_archive_paths and dest_path.exists():
                skipped_existing.append({**row, "dest_path": str(dest_path), "reason": "resume-state"})
                continue

            if dest_path.exists():
                skipped_existing.append({**row, "dest_path": str(dest_path)})
                completed_archive_paths.add(archive_path)
                continue

            matches = by_basename.get(basename, [])
            if not matches:
                matches = choose_version_fallback(row, remote_version_candidates)
                if not matches:
                    missing_remote.append(row)
                    continue
            if len(matches) > 1:
                ambiguous_rows.append({**row, "remote_path_count": len(matches)})
                ambiguous.extend({**row, "remote_path": match, "remote_path_count": len(matches)} for match in matches)
                continue

            remote_path = matches[0]
            used_version_fallback = Path(remote_path).name != basename
            print(f"Downloading [{index}/{total}] {archive_path}", flush=True)
            if not args.dry_run:
                temp_target = temp_dir / basename
                if temp_target.exists():
                    temp_target.unlink()
                try:
                    pull_archives.run(
                        pull_archives.render_command(
                            get_cmd_template,
                            remote=remote_ref,
                            path=pull_archives.normalize_remote_path_for_get(remote_path),
                            dest=str(temp_dir),
                        )
                    )
                    downloaded_files = sorted(temp_dir.glob("*.lha"), key=lambda path: path.stat().st_mtime, reverse=True)
                    actual_temp_path = temp_target if temp_target.exists() else (downloaded_files[0] if downloaded_files else None)
                    if actual_temp_path is None or not actual_temp_path.exists():
                        raise RuntimeError(f"Download did not produce an archive in {temp_dir}")
                    shutil.move(str(actual_temp_path), str(dest_path))
                except Exception as err:
                    failed.append({**row, "remote_path": remote_path, "dest_path": str(dest_path), "error": str(err)})
                    print(f"Failed: {archive_path} ({err})", file=sys.stderr)
                    continue
            download_entry = {**row, "remote_path": remote_path, "dest_path": str(dest_path)}
            if used_version_fallback:
                downloaded_version_fallback.append({
                    **download_entry,
                    "requested_basename": basename,
                    "downloaded_basename": Path(remote_path).name,
                })
            downloaded.append(download_entry)
            completed_archive_paths.add(archive_path)
            save_json(state_path, {"completed_archive_paths": sorted(completed_archive_paths)})

        write_tsv(
            reports_dir / "downloaded.tsv",
            ["id", "archive_path", "basename", "top_level", "remote_path", "dest_path"],
            downloaded,
        )
        write_tsv(
            reports_dir / "downloaded_version_fallback.tsv",
            ["id", "archive_path", "basename", "top_level", "requested_basename", "downloaded_basename", "remote_path", "dest_path"],
            downloaded_version_fallback,
        )
        write_tsv(
            reports_dir / "skipped_existing.tsv",
            ["id", "archive_path", "basename", "top_level", "dest_path", "reason"],
            skipped_existing,
        )
        write_tsv(
            reports_dir / "missing_remote.tsv",
            ["id", "archive_path", "basename", "top_level"],
            missing_remote,
        )
        write_tsv(
            reports_dir / "ambiguous.tsv",
            ["id", "archive_path", "basename", "top_level", "remote_path_count", "remote_path"],
            ambiguous,
        )
        write_tsv(
            reports_dir / "failed.tsv",
            ["id", "archive_path", "basename", "top_level", "remote_path", "dest_path", "error"],
            failed,
        )

        summary = {
            "csv": str(csv_path),
            "dest": str(dest_root),
            "reports_dir": str(reports_dir),
            "total_unique_archive_paths": total,
            "downloaded": len(downloaded),
            "downloaded_version_fallback": len(downloaded_version_fallback),
            "skipped_existing": len(skipped_existing),
            "missing_remote": len(missing_remote),
            "ambiguous_archive_paths": len(ambiguous_rows),
            "ambiguous_matches": len(ambiguous),
            "failed": len(failed),
            "dry_run": args.dry_run,
            "resume_state": str(state_path),
        }
        save_json(state_path, {"completed_archive_paths": sorted(completed_archive_paths)})
        save_json(reports_dir / "summary.json", summary)

        print()
        print("Summary")
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 1 if failed else 0
    finally:
        if logged_in and logout_cmd_template:
            try:
                pull_archives.run(
                    pull_archives.render_command(logout_cmd_template, remote=remote_ref, path="", dest=str(titles_root))
                )
            except Exception as err:
                print(f"Warning: logout failed: {err}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
