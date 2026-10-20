#!/usr/bin/env python3
"""Audit selected game containers against local files and an upstream path listing.

The upstream listing is the output of mega-find / --pattern=*.lha. Comparisons
keep language, chipset, memory, timing and content-edition suffixes distinct.
Newer filename versions are candidates, not proof of runtime compatibility.
"""
import argparse
import csv
import json
import os
from collections import defaultdict
from pathlib import Path

from promote_newer_archives import parse_archive_name, archive_revision_key, variant_suffix


def family(parsed):
    return parsed['name'].casefold(), variant_suffix(parsed['suffix'])


def inventory(csv_path, titles_dir, upstream_paths=()):
    with csv_path.open(newline='') as handle:
        rows = list(csv.DictReader(handle, delimiter=';'))
    candidates = defaultdict(list)
    for path in titles_dir.rglob('*.lha'):
        relative = path.relative_to(titles_dir)
        if relative.parts[0] not in ('game', 'game-notwhdl', 'manual-downloads'):
            continue
        if 'retired' in relative.parts:
            continue
        parsed = parse_archive_name(path.name)
        if parsed:
            candidates[family(parsed)].append((archive_revision_key(parsed), path.name, str(path), 'local'))
    for value in upstream_paths:
        parsed = parse_archive_name(Path(value).name)
        if parsed and ' - Games' in value and 'WHDLoad - Games' in value:
            candidates[family(parsed)].append((archive_revision_key(parsed), Path(value).name, value, 'upstream'))
    result = []
    for row in rows:
        if row['category'].casefold() != 'game':
            continue
        selected = row['archive_path']
        parsed = parse_archive_name(Path(selected).name)
        item = {key: row[key] for key in ('id', 'title', 'hardware', 'language', 'archive_path', 'slave_path', 'slave_version')}
        item['archive_exists'] = bool(selected) and (titles_dir / selected).is_file()
        if not parsed:
            item['status'] = 'unversioned' if selected else 'no archive'
        else:
            newer = [c for c in candidates[family(parsed)] if c[0] > archive_revision_key(parsed)]
            item['status'] = 'newer available' if newer else 'current in inventory'
            if newer:
                # Prefer a local copy when the same version is also upstream.
                best = max(newer, key=lambda c: (c[0], c[3] == 'local'))
                item['latest_archive'] = best[1]
                item['source'] = best[2]
                item['availability'] = best[3]
        result.append(item)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, default=Path('data/db/titles.csv'))
    parser.add_argument('--titles-dir', type=Path, default=Path(os.getenv('AGSCONTENT', 'content')) / 'titles')
    parser.add_argument('--upstream-list', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    upstream = args.upstream_list.read_text().splitlines() if args.upstream_list else []
    rows = inventory(args.csv, args.titles_dir, upstream)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + '\n')
    counts = {status: sum(r['status'] == status for r in rows) for status in sorted({r['status'] for r in rows})}
    print(json.dumps({'game_entries': len(rows), 'statuses': counts, 'missing_archives': sum(not r['archive_exists'] for r in rows)}, indent=2))


if __name__ == '__main__':
    main()
