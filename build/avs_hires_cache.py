"""Synchronize a hi-res launcher by content, without cloning its whole tree."""
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat

from avs_artwork import is_nsfw

SUFFIXES = ['.iff', '-QR.iff'] + [f'-{i}.iff' for i in range(1, 10)]


def preserve_hires_tree(hires, saved):
    """Keep the published tree clear of shared layers, including on retry."""
    hires, saved = Path(hires), Path(saved)
    active = Path(str(saved) + '.active')
    if hires.is_dir() and not active.exists():
        if saved.exists():
            shutil.rmtree(saved)  # Retire the old duplicate cache once.
        os.replace(hires, saved)
    active.touch()


def file_plan(medium, collection):
    medium = Path(medium)
    artwork, launcher = Path('data/img_highres'), Path('data/avs-highres')
    plan, directories = {}, set()
    title_images = {name + suffix for name in collection.image_entries for suffix in SUFFIXES}
    for directory, dirs, files in os.walk(medium):
        relative = Path(directory).relative_to(medium)
        directories.update((relative / name).as_posix() for name in dirs)
        for name in files:
            if name == '.DS_Store' or fnmatch.fnmatch(name, 'skin-empty*.iff') or name.lower().endswith('-qr2.iff'):
                continue
            source = Path(directory) / name
            key = (relative / name).as_posix()
            if (source.suffix == '.iff' and key not in title_images
                    and not name.startswith('skin-') and not source.stem.lower().endswith('-qr')):
                source = artwork / key
                if not source.is_file():
                    raise FileNotFoundError(f'Missing static hi-res artwork: {source}')
                # Navigation slides can exist only in hi-res artwork; the
                # medium menu need not carry dummy numbered images for them.
                for index in range(1, 10):
                    slide = source.with_name(source.stem + f'-{index}.iff')
                    if slide.is_file():
                        plan[(relative / slide.name).as_posix()] = slide
            plan[key] = source
    if (launcher/'About-QR2.iff').is_file():
        # Also retire an active About QR inherited from an older medium cache.
        for key in list(plan):
            if key.lower() == 'about-qr.iff':
                del plan[key]
    for source in launcher.rglob('*'):
        if source.is_file() and source.name != '.DS_Store' and not source.name.lower().endswith('-qr2.iff'):
            plan[source.relative_to(launcher).as_posix()] = source
    plan['AVS.conf.base'] = launcher / 'AVS.conf'
    images = {}
    for source in sorted(artwork.glob('*.iff')) + sorted((artwork / 'qr').glob('*.iff')):
        images.setdefault(source.stem, source)
    for source in sorted(launcher.glob('*-qr.iff')):
        images.setdefault(source.stem, source)
    for name, entry_id in collection.image_entries.items():
        for suffix in SUFFIXES:
            plan.pop(name + suffix, None)
        if is_nsfw(collection.by_id.get(entry_id, {})):
            pattern = re.compile(re.escape(name) + r'(?:-\d+|-qr)?\.iff', re.I)
            for key in list(plan):
                if pattern.fullmatch(key):
                    del plan[key]
            plan[name + '.iff'] = artwork / 'NSFW.iff'
            continue
        for key, suffix in [(entry_id, '.iff'), (entry_id + '-qr', '-QR.iff')] + [
                (entry_id + f'-{i}', f'-{i}.iff') for i in range(1, 10)]:
            if key in images:
                plan[name + suffix] = images[key]
        if name + '.iff' not in plan:
            for index in [3, 2, 1, 4, 5, 6, 7, 8, 9]:
                if name + f'-{index}.iff' in plan:
                    plan[name + '.iff'] = plan[name + f'-{index}.iff']
                    break
    return plan, directories


def signature(path):
    return stat_signature(path.stat())


def stat_signature(info):
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, stat.S_IMODE(info.st_mode)]


def inventory(root):
    """Collect each output's metadata once, without following symlinks."""
    files, directories, links = {}, set(), set()
    pending = [('', root)]
    while pending:
        relative, directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                key = relative + entry.name
                if entry.is_symlink():
                    links.add(key)
                    continue
                info = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    directories.add(key)
                    pending.append((key + '/', Path(entry.path)))
                else:
                    files[key] = stat_signature(info)
    return files, directories, links


def content_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def sync_hires_tree(medium, destination, collection, manifest_path):
    """Validate outputs as well as inputs; interrupted runs can safely resume."""
    destination, manifest_path = Path(destination), Path(manifest_path)
    plan, directories = file_plan(medium, collection)
    try:
        previous = json.loads(manifest_path.read_text())
        if previous.get('schema') != 1:
            previous = {}
    except (OSError, ValueError):
        previous = {}
    sources, outputs = {}, {}
    copied = reused = removed = 0
    destination.mkdir(parents=True, exist_ok=True)
    existing, existing_dirs, links = inventory(destination)
    # Remove stale files before directories are created, including file/dir swaps.
    for key in links | (existing.keys() - plan.keys()):
        (destination / key).unlink()
        removed += 1
    for key in existing_dirs & plan.keys():
        shutil.rmtree(destination / key)
    # Include parents supplied by launcher overlays, even if absent in medium.
    for key in plan:
        parent = key.rpartition('/')[0]
        while parent and parent not in directories:
            directories.add(parent)
            parent = parent.rpartition('/')[0]
    for key in sorted(directories - existing_dirs):
        (destination / key).mkdir(parents=True, exist_ok=True)
    for key, source in sorted(plan.items()):
        source_key = str(source)
        record = sources.get(source_key)
        if record is None:
            source_signature = signature(source)
            old = previous.get('sources', {}).get(source_key, {})
            digest = old.get('hash') if old.get('signature') == source_signature else None
            record = {'signature': source_signature, 'hash': digest or content_hash(source)}
            sources[source_key] = record
        target = destination / key
        current = existing.get(key)
        old = previous.get('outputs', {}).get(key, {})
        digest = old.get('hash') if current is not None and old.get('signature') == current else None
        if current is not None and digest is None:
            digest = content_hash(target)
        if digest == record['hash']:
            if current[-1] != record['signature'][-1]:
                target.chmod(record['signature'][-1])
                current = signature(target)
            reused += 1
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + '.hires-tmp')
            shutil.copy2(source, temporary)
            os.replace(temporary, target)
            current = signature(target)
            copied += 1
        outputs[key] = {'signature': current, 'hash': record['hash']}
    # Retain intentional empty menu directories, remove obsolete folders.
    for key in sorted(existing_dirs - directories, key=lambda key: key.count('/'), reverse=True):
        try:
            (destination / key).rmdir()
        except OSError:
            pass
    temporary = manifest_path.with_name(manifest_path.name + '.tmp')
    temporary.write_text(json.dumps({'schema': 1, 'sources': sources, 'outputs': outputs}))
    os.replace(temporary, manifest_path)
    print(f' > HiRes: copied {copied}, reused {reused}, removed {removed} files')
    return outputs
