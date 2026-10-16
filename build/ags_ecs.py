"""Shared ECS family selection for curated menus and automatic collections."""
import json
import re
import struct
from collections import defaultdict
from pathlib import Path

from pull_archives import is_low_memory_archive


def make_sanitizer(sanitize):
    """Verify the installed slave as well as database chipset metadata."""
    from lhafile import LhaFile
    import ags_paths
    cache = {}
    excluded = []

    def checked(row):
        entry = sanitize(row)
        if not entry or not entry.get('slave_path'):
            return entry
        key = (entry['archive_path'], entry['slave_path'].lower())
        if key not in cache:
            reason = None
            try:
                archive = LhaFile(str(Path(ags_paths.titles())/entry['archive_path']))
                names = {name.replace(chr(92), '/').lower(): name for name in archive.namelist()}
                original = names[entry['slave_path'].replace(chr(92), '/').lower()]
                data = archive.read(original)
                signature = data.find(b'WHDLOADS', 0, 256)
                if signature < 4:
                    reason = 'invalid WHDLoad slave header'
                elif struct.unpack_from('>H', data, signature+10)[0] & 32:
                    reason = 'slave requires AGA despite database metadata'
            except Exception as exc:
                reason = str(exc)
            cache[key] = reason
            if reason:
                excluded.append({'id': entry['id'], 'title': entry['title'], 'status': 'invalid-slave',
                                 'reason': reason, 'selected': None, 'candidates': []})
        return entry if cache[key] is None else None

    checked.excluded = excluded
    return checked


def requires_aga(entry):
    return str(entry.get('aga') or '').strip() == '1' or bool(
        re.search(r'(?:^|[^A-Z0-9])(?:AGA|CD32)(?:$|[^A-Z0-9])',
                  (entry.get('hardware') or '').upper()))


def candidate_rank(entry, root_id):
    """Expanded-memory versions always outrank low-memory versions."""
    return (
        is_low_memory_archive(entry.get('archive_path') or ''),
        entry['id'] != root_id,
        bool(entry.get('issues')),
        'English' not in (entry.get('language') or 'English'),
        bool(re.search(r'MT.?32|CDTV|Arcadia', entry.get('hardware') or '', re.I)),
    )


class ECSSelector:
    def __init__(self, rows, sanitize, overrides=None):
        self.rows = {r['id']: dict(r) for r in rows}
        self.roots = {}
        self.selected = {}
        self.report = []
        families = defaultdict(list)
        for entry_id in self.rows:
            seen = set()
            root = entry_id
            error = None
            while self.rows[root].get('preferred_version'):
                if root in seen:
                    error = 'preferred-version cycle'
                    break
                seen.add(root)
                preferred = self.rows[root]['preferred_version']
                if preferred not in self.rows:
                    error = 'missing preferred version: ' + preferred
                    break
                root = preferred
            if error:
                self.report.append({'id': entry_id, 'title': self.rows[entry_id]['title'],
                                    'status': 'invalid-link', 'reason': error, 'selected': None, 'candidates': []})
                continue
            self.roots[entry_id] = root
            families[root].append(self.rows[entry_id])
        overrides = overrides or {}
        unknown = set(overrides) - set(families)
        if unknown:
            raise ValueError('Unknown ECS override families: ' + ', '.join(sorted(unknown)))
        for root, members in families.items():
            candidates = [sanitize(r) for r in members if not requires_aga(r)]
            candidates = [r for r in candidates if r]
            candidates.sort(key=lambda r: (candidate_rank(r, root), r['id']))
            winner = None
            status = 'unavailable'
            if candidates:
                best = candidate_rank(candidates[0], root)
                tied = [r for r in candidates if candidate_rank(r, root) == best]
                if len(tied) == 1:
                    winner = tied[0]
                else:
                    status = 'ambiguous'
                override = overrides.get(root)
                if override:
                    match = next((r for r in candidates if r['id'] == override), None)
                    if not match:
                        raise ValueError(f'Invalid/incompatible ECS override for {root}: {override}')
                    if is_low_memory_archive(match.get('archive_path') or '') and any(
                            not is_low_memory_archive(r.get('archive_path') or '') for r in candidates):
                        raise ValueError(f'Low-memory ECS override outranks expanded-memory candidate: {root}')
                    winner = match
                if winner:
                    winner = dict(winner, _ecs_family=root)
                    status = 'canonical' if winner['id'] == root else 'fallback'
            elif root in overrides:
                raise ValueError('ECS override has no compatible launchable candidates: ' + root)
            self.selected[root] = winner
            self.report.append({'id': root, 'title': self.rows[root]['title'], 'status': status,
                                'selected': winner['id'] if winner else None,
                                'candidates': [r['id'] for r in candidates]})

    def resolve(self, entry_id):
        return self.selected.get(self.roots.get(entry_id, entry_id))

    def write_report(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(self.report, indent=2) + '\n')


class ECSDatabase:
    """Keep the original database available for lookup and family relationships."""
    def __init__(self, db, selector):
        self.db = db
        self.ecs_selector = selector

    def __getattr__(self, name):
        return getattr(self.db, name)


def prepare_menu(ags_path):
    """Remove unavailable resolution switches and empty chipset-only folders."""
    import os
    import shutil
    root = Path(ags_path)
    for path in (root/'[ Options ].ags').glob('Launcher Res*'):
        if path.is_file():
            path.unlink()
    for directory, _, _ in os.walk(root, topdown=False):
        folder = Path(directory)
        if folder.suffix != '.ags':
            continue
        # About and other note-only sections are valid selectable entries.
        # Their content lives beside the directory, not inside it.
        if folder.with_suffix('.txt').is_file():
            continue
        if not any(folder.glob('*.run')) and not any(folder.glob('*.ags')):
            shutil.rmtree(folder)
            for suffix in ['.txt', '.iff']:
                sibling = folder.with_suffix(suffix)
                if sibling.is_file():
                    sibling.unlink()


def patch_menu_text_pen(source, destination):
    """Use locked white for text instead of AGS2Menu's hard-coded AGA pen 253.

    The instruction loads D0 before graphics.library/SetAPen (-342). On a
    four-plane screen pen 253 becomes dynamic slot 13; pen 255 becomes locked
    slot 15. Match the complete instruction/call sequence and fail if a future
    launcher changes it. No relocation or instruction size changes are needed.
    """
    original = Path(source).read_bytes()
    sequence = bytes.fromhex('203c000000fd2f4000002c6cffcc4cdf02014eaefeaa')
    if original.count(sequence) != 1:
        raise ValueError('Unknown AGS2Menu text-pen code; review the ECS patch')
    replacement = sequence[:5] + b'\xff' + sequence[6:]
    Path(destination).write_bytes(original.replace(sequence, replacement))


def install_launcher(ags_path, collection, image_root='data/img_ecs'):
    """Replace generated menu images with pre-rendered hi-res ECS artwork."""
    import hashlib
    import shutil
    root = Path(ags_path)
    patch_menu_text_pen('data/ags2/AGS2Menu', root/'AGS2Menu')
    static = Path(image_root)
    manifest_path = static/'manifest.json'
    if not manifest_path.is_file():
        raise FileNotFoundError('Static ECS artwork missing; run make ecs-artwork first')
    manifest = json.loads(manifest_path.read_text())
    from ecs_artwork import VERSION
    if manifest.get('version') != VERSION:
        raise ValueError('Static ECS artwork is outdated; run make ecs-artwork')

    def copy(relative, destination, launcher=False):
        original = Path('data/ags2-highres' if launcher else 'data/img_highres')/relative
        source = static/('launcher' if launcher else '')/relative
        expected = manifest['sources'].get(str(original))
        if not source.is_file() or not expected or hashlib.sha256(original.read_bytes()).hexdigest() != expected:
            raise FileNotFoundError(f'Missing/stale ECS artwork {source}; run make ecs-artwork')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    title_images = {path+suffix for path in collection.image_entries
                    for suffix in ['.iff','-QR.iff']+[f'-{i}.iff' for i in range(1,10)]}
    for image in list(root.rglob('*.iff')):
        rel = image.relative_to(root)
        if str(rel) in title_images or image.name.startswith('skin-') or image.stem.lower().endswith('-qr'):
            image.unlink()
            continue
        copy(rel, image)
    fallback_artwork = []
    missing = []
    for relpath, entry_id in collection.image_entries.items():
        entry = collection.by_id.get(entry_id, {})
        artwork_id = entry_id
        if not any((static/(artwork_id+suffix)).is_file() for suffix in ['.iff']+[f'-{i}.iff' for i in range(1,10)]):
            artwork_id = entry.get('_ecs_family', entry_id)
            if artwork_id != entry_id:
                fallback_artwork.append({'id': entry_id, 'artwork': artwork_id})
        base = root/relpath
        found = False
        for key, suffix in [(artwork_id,'.iff'), (artwork_id+'-qr','-QR.iff')]+[
                (artwork_id+f'-{i}',f'-{i}.iff') for i in range(1,10)]:
            relative = Path(key+'.iff')
            if not (static/relative).is_file():
                relative = Path('qr')/relative
            if (static/relative).is_file():
                copy(relative, Path(str(base)+suffix))
                found = found or suffix != '-QR.iff'
        if found and not Path(str(base)+'.iff').is_file():
            for index in [3,2,1,4,5,6,7,8,9]:
                slide = Path(str(base)+f'-{index}.iff')
                if slide.is_file():
                    shutil.copyfile(slide, str(base)+'.iff')
                    break
        if not found:
            missing.append(entry_id)
    for name in ['skin-bg-highres.iff','skin-empty-highres.iff','About-qr.iff']:
        copy(Path(name), root/name, launcher=True)
    config = Path('data/ags2-ecs/AGS2.conf')
    for name in ['AGS2.conf','AGS2.conf.base']:
        shutil.copyfile(config, root/name)
    for path in (root/'[ Options ].ags').glob('Launcher Res*'):
        if path.is_file():
            path.unlink()
    (root/'ecs-artwork-report.json').write_text(json.dumps({
        'palette_version': manifest['version'],
        'canonical_artwork_fallbacks': fallback_artwork, 'missing': sorted(set(missing))}, indent=2)+'\n')
    print(f' > ECS artwork: {len(set(missing))} missing titles; {len(fallback_artwork)} canonical artwork fallbacks')
