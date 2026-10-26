"""Shared ECS family selection for curated menus and automatic collections."""
import json
import re
import struct
from collections import defaultdict
from pathlib import Path

from avs_artwork import is_nsfw, install_nsfw_thumbnail


def make_sanitizer(sanitize):
    """Verify the installed slave as well as database chipset metadata."""
    from lhafile import LhaFile
    import avs_paths
    cache = {}
    chip_memory = {}
    excluded = []

    def checked(row):
        entry = sanitize(row)
        if not entry or not entry.get('slave_path'):
            return entry
        key = (entry['archive_path'], entry['slave_path'].lower())
        if key not in cache:
            reason = None
            try:
                archive = LhaFile(str(Path(avs_paths.titles())/entry['archive_path']))
                names = {name.replace(chr(92), '/').lower(): name for name in archive.namelist()}
                original = names[entry['slave_path'].replace(chr(92), '/').lower()]
                data = archive.read(original)
                signature = data.find(b'WHDLOADS', 0, 256)
                if signature < 4:
                    reason = 'invalid WHDLoad slave header'
                elif struct.unpack_from('>H', data, signature+10)[0] & 32:
                    reason = 'slave requires AGA despite database metadata'
                else:
                    chip_memory[key] = struct.unpack_from('>I', data, signature+12)[0]
            except Exception as exc:
                reason = str(exc)
            cache[key] = reason
            if reason:
                excluded.append({'id': entry['id'], 'title': entry['title'], 'status': 'invalid-slave',
                                 'reason': reason, 'selected': None, 'candidates': []})
        if cache[key] is not None:
            return None
        return dict(entry, _ecs_chip_memory=chip_memory[key])

    checked.excluded = excluded
    return checked


def requires_aga(entry):
    return str(entry.get('aga') or '').strip() == '1' or bool(
        re.search(r'(?:^|[^A-Z0-9])(?:AGA|CD32)(?:$|[^A-Z0-9])',
                  (entry.get('hardware') or '').upper()))


def memory_rank(path):
    """Prefer explicit 512KB, 1MB, and LowMem variants to unspecified ones."""
    name = Path(path).name
    for rank, label in enumerate(['512k(?:b)?', '1mb(?:chip)?', 'lowmem(?:ory)?|lowram']):
        if re.search(r'(?:^|_)(?:' + label + r')(?:_|\.)', name, re.I):
            return rank
    return 3


def candidate_rank(entry, root_id, root_entry=None, minimize_chip=True):
    """Keep language/region/features, then minimize required chip RAM."""
    root_entry = root_entry or {}
    memory = memory_rank(entry.get('archive_path') or '')
    return (
        (root_entry.get('language') or 'English').split(',')[0].strip() not in
        [language.strip() for language in (entry.get('language') or 'English').split(',')],
        str(entry.get('ntsc') or '0') != str(root_entry.get('ntsc') or '0'),
        bool(re.search(r'MT.?32|CDTV|Arcadia', entry.get('hardware') or '', re.I)) !=
        bool(re.search(r'MT.?32|CDTV|Arcadia', root_entry.get('hardware') or '', re.I)),
        entry.get('_ecs_chip_memory', [524288, 1048576, 1572864, 2097152][memory]) if minimize_chip else 0,
        memory,
        re.split(r'_v|_Beta', Path(entry.get('archive_path') or '').name, flags=re.I)[0].lower() !=
        re.split(r'_v|_Beta', Path(root_entry.get('archive_path') or '').name, flags=re.I)[0].lower(),
        bool(entry.get('issues')),
        entry['id'] != root_id,
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
            # Header differences alone must not replace unrelated standard
            # variants (for example a crunched or speech-free release).
            minimize_chip = any(memory_rank(r.get('archive_path') or '') < 3 for r in candidates)
            def rank(entry):
                return candidate_rank(entry, root, self.rows[root], minimize_chip)
            candidates.sort(key=lambda r: (rank(r), r['id']))
            winner = None
            status = 'unavailable'
            if candidates:
                best = rank(candidates[0])
                tied = [r for r in candidates if rank(r) == best]
                if len(tied) == 1:
                    winner = tied[0]
                else:
                    status = 'ambiguous'
                override = overrides.get(root)
                if override:
                    match = next((r for r in candidates if r['id'] == override), None)
                    if not match:
                        raise ValueError(f'Invalid/incompatible ECS override for {root}: {override}')
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


def prepare_menu(avs_path):
    """Remove unavailable resolution switches and empty chipset-only folders."""
    import os
    import shutil
    root = Path(avs_path)
    for path in (root/'Options.avs').glob('Launcher Res*'):
        if path.is_file():
            path.unlink()
    for directory, _, _ in os.walk(root, topdown=False):
        folder = Path(directory)
        if folder.suffix != '.avs':
            continue
        # About and other note-only sections are valid selectable entries.
        # Their content lives beside the directory, not inside it.
        if folder.with_suffix('.txt').is_file():
            continue
        if not any(folder.glob('*.run')) and not any(folder.glob('*.avs')):
            shutil.rmtree(folder)
            for suffix in ['.txt', '.iff']:
                sibling = folder.with_suffix(suffix)
                if sibling.is_file():
                    sibling.unlink()


def install_launcher(avs_path, collection, image_root='data/img_ecs', launcher_root='data/avs-ecs'):
    """Replace generated menu images with pre-rendered hi-res ECS artwork."""
    import shutil
    root = Path(avs_path)
    shutil.copyfile(Path(launcher_root)/'AVSMenu', root/'AVSMenu')
    static = Path(image_root)
    def copy(relative, destination, launcher=False):
        source = (Path(launcher_root) if launcher else static)/relative
        if not source.is_file():
            raise FileNotFoundError(f'Missing ECS artwork {source}; run make ecs-artwork')
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
        if is_nsfw(entry):
            install_nsfw_thumbnail(base, "ecs")
            continue
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
    for name in ['skin-bg-highres.iff','AmigaVisionEmpty.iff','About-qr.iff']:
        copy(Path(name), root/name, launcher=True)
    config = Path(launcher_root)/'AVS.conf'
    for name in ['AVS.conf','AVS.conf.base']:
        shutil.copyfile(config, root/name)
    for path in (root/'Options.avs').glob('Launcher Res*'):
        if path.is_file():
            path.unlink()
    (root/'ecs-artwork-report.json').write_text(json.dumps({
        'canonical_artwork_fallbacks': fallback_artwork, 'missing': sorted(set(missing))}, indent=2)+'\n')
    print(f' > ECS artwork: {len(set(missing))} missing titles; {len(fallback_artwork)} canonical artwork fallbacks')
