#!/usr/bin/env python3
"""Import unambiguous staged WHDLoad counterparts without changing curated rows.

Run after pull_archives.py --backfill-non-aga. Unknown families and ambiguous
matches remain staged and are written to a JSON review report.
"""
import argparse
import csv
import json
import os
import re
import shutil
import struct
from collections import defaultdict
from pathlib import Path

from lhafile import LhaFile
from avs_index import infer_aga_flag, infer_hardware_from_archive, infer_language_from_archive
from promote_newer_archives import parse_archive_name, archive_revision_key, variant_suffix

SHARED_FIELDS = ('title', 'title_short', 'category', 'subcategory', 'developer',
                 'publisher', 'players', 'country')
SAFE_VARIANTS = {'ocs', 'ecs', 'nonaga', 'ntsc', 'pal', '512k', '1mb', '2mb',
                 'chip', 'fast', 'slow', 'files', 'image', '1disk', '2disk',
                 'lowmem', 'cd', 'cdtv', 'mt32', 'altversion', 'early2disk',
                 'fasterversion', 'a1200version', 'crunched', 'nospeech', 'beta', 'prerelease',
                 'en', 'de', 'fr', 'es', 'it', 'pl', 'dk', 'se', 'nl', 'pt',
                 'gr', 'ru', 'fi', 'shareware'}


def family(name):
    # Only exact archive-family names; do not fuzzy-match different games.
    parsed = parse_archive_name(Path(name).name)
    return parsed['name'].casefold() if parsed else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--titles-dir', type=Path, default=Path(os.environ.get('AVSCONTENT', 'content')) / 'titles')
    parser.add_argument('--csv', type=Path, default=Path('data/db/titles.csv'))
    parser.add_argument('--report', type=Path, default=Path('data/db/ecs-backfill-report.json'))
    parser.add_argument('--inventory', type=Path, help='Upstream path inventory (defaults to source/upstream-inventory.json)')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    with args.csv.open(newline='') as f:
        reader = csv.DictReader(f, delimiter=';')
        header = reader.fieldnames
        rows = list(reader)
    ids = {r['id']: r for r in rows}
    inventory_path = args.inventory or args.source / 'upstream-inventory.json'
    if not inventory_path.exists():
        parser.error('Upstream inventory required; run the archive backfill first or pass --inventory')
    inventory = json.loads(inventory_path.read_text())
    collections = {Path(p).name: p for p in inventory}
    donors = defaultdict(list)
    slave_donors = defaultdict(list)
    for row in rows:
        if row['category'] != 'Game':
            continue
        if row['slave_path']:
            slave_donors[Path(row['slave_path']).name.lower()].append(row)
        if row['archive_path'] and family(row['archive_path']):
            donors[family(row['archive_path'])].append(row)
    report = []
    candidates = defaultdict(list)
    for path in sorted(args.source.glob('*.lha')):
        if re.search(r'(?:^|_)(AGA|CD32|JST)(?:_|\.)', path.name, re.I) or '_HD_' in path.name:
            continue
        collection = collections.get(path.name, '')
        if not collection:
            report.append({'archive': path.name, 'status': 'review', 'reason': 'archive not in upstream inventory'})
            continue
        if ' - Games' not in collection:
            report.append({'archive': path.name, 'status': 'deferred', 'reason': 'non-game collection'})
            continue
        try:
            archive = LhaFile(str(path))
            slave_paths = [n for n in archive.namelist()
                           if n.lower().endswith('.slave') and len(n.replace(chr(92), '/').split('/')) <= 2]
            slaves = [n.replace(chr(92), '/') for n in slave_paths]
            for original in slave_paths:
                data = archive.read(original)
                signature = data.find(b'WHDLOADS', 0, 256)
                if signature < 4:
                    raise ValueError('invalid WHDLoad slave header')
                # ws_Flags, WHDLB_ReqAGA: see upstream include/whdload.i.
                if struct.unpack_from('>H', data, signature + 10)[0] & (1 << 5):
                    raise ValueError('slave requires AGA despite archive filename')
        except Exception as exc:
            report.append({'archive': path.name, 'status': 'review', 'reason': str(exc)})
            continue
        existing = ['game--' + n[:-6].replace('/', '--').lower() for n in slaves]
        if existing and all(key in ids for key in existing):
            report.append({'archive': path.name, 'status': 'existing', 'ids': existing})
            continue
        if len(slaves) != 1:
            report.append({'archive': path.name, 'status': 'review', 'reason': 'expected one WHDLoad slave', 'slaves': slaves})
            continue
        parsed = parse_archive_name(path.name)
        if parsed and set(variant_suffix(parsed['suffix'])) - SAFE_VARIANTS:
            report.append({'archive': path.name, 'status': 'review', 'reason': 'special variant requires metadata review'})
            continue
        matches = donors.get(family(path.name), [])
        if not matches:
            # Repacked collections (e.g. Time Runners) may change the directory
            # while retaining the exact slave filename. Never fuzzy-match it.
            matches = slave_donors.get(Path(slaves[0]).name.lower(), [])
        language = infer_language_from_archive(path.name)
        language_matches = [r for r in matches if (language or 'English') in
                   [value.strip() for value in (r['language'] or 'English').split(',')]]
        # A newly found translation may have no same-language row. Descriptive
        # game metadata can still come from the unique known game family.
        matches = language_matches or matches
        matches = [r for r in matches if len(r['id'].split('--')) == 3 and r['hardware'] != 'Arcadia']
        roots = set()
        for row in matches:
            seen = set()
            while row.get('preferred_version') in ids and row['id'] not in seen:
                seen.add(row['id'])
                row = ids[row['preferred_version']]
            if row['id'] not in seen and not row.get('preferred_version'):
                roots.add(row['id'])
        if len(roots) != 1:
            report.append({'archive': path.name, 'status': 'review', 'reason': 'no unique existing family/language', 'matches': sorted(roots)})
            continue
        donor = ids[next(iter(roots))]
        if not donor['slave_path'] or not (args.titles_dir / donor['archive_path']).is_file():
            report.append({'archive': path.name, 'status': 'review', 'reason': 'canonical counterpart is not locally launchable'})
            continue
        if donor['category'] != 'Game':
            report.append({'archive': path.name, 'status': 'review', 'reason': 'non-game content'})
            continue
        slave = slaves[0]
        entry_id = existing[0]
        candidates[entry_id].append((path, slave, donor))
    added = []
    for entry_id, options in sorted(candidates.items()):
        path, slave, donor = max(options, key=lambda item: archive_revision_key(parse_archive_name(item[0].name)))
        if len({item[2]['id'] for item in options}) != 1:
            report.append({'id': entry_id, 'status': 'review', 'reason': 'conflicting canonical counterparts'})
            continue
        relative = Path(donor['archive_path']).parent / path.name
        row = dict.fromkeys(header, '')
        row.update({k: donor[k] for k in SHARED_FIELDS})
        row.update(id=entry_id, redundant='1', preferred_version=donor['id'],
                   hardware=infer_hardware_from_archive(str(relative)), aga=infer_aga_flag(str(relative)),
                   ntsc='1' if 'NTSC' in path.stem.upper().split('_') else '',
                   language=infer_language_from_archive(str(relative)), archive_path=str(relative),
                   slave_path=slave, slave_version='v' + parse_archive_name(path.name)['version'].removeprefix('v'))
        # IDs, release date, launch arguments, issue flags, and video settings
        # may differ between releases; deliberately do not inherit them.
        target = args.titles_dir / relative
        if target.exists() and target.read_bytes() != path.read_bytes():
            report.append({'archive': path.name, 'status': 'review', 'reason': 'different destination archive exists'})
            continue
        if args.apply:
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                shutil.copy2(path, target)
        added.append(row)
        report.append({'archive': path.name, 'status': 'added' if args.apply else 'would-add', 'id': entry_id, 'preferred_version': donor['id']})
    if args.apply and added:
        temporary = args.csv.with_suffix('.csv.tmp')
        with temporary.open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=header, delimiter=';', lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows + added)
        temporary.replace(args.csv)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    counts = defaultdict(int)
    for entry in report:
        counts[entry['status']] += 1
    print(dict(counts))
    print('Review report:', args.report)


if __name__ == '__main__':
    main()
