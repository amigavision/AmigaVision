"""Transactional PFS image updates using the existing Amiberry cloner.

A sidecar describes only the last successfully published image. Unknown or
externally modified images are rebuilt, never assumed to match a staging tree.
"""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat as stat_module
from time import perf_counter
import subprocess
import uuid

SCHEMA = 1
PLAN_NAME = 'image-update-plan.json'
IGNORED = {'.DS_Store', 'Thumbs.db', '__MACOSX'}
PARTITIONS = {'DH0': 'Amiga', 'DH1': 'Data'}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    temp = path.with_name(path.name + '.tmp')
    with temp.open('w') as f:
        json.dump(value, f, sort_keys=True, separators=(',', ':'))
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def prepare_plan(workspace, image, partitions, profile, filesystem, image_size_bytes=0, boot_extra_bytes=0):
    atomic_json(Path(workspace) / PLAN_NAME, {
        'schema': SCHEMA, 'image': str(Path(image).resolve()),
        'partitions': partitions if partitions is not None else [['DH0', 0], ['DH1', 0]],
        'deferred_layout': partitions is None, 'boot_extra_bytes': boot_extra_bytes,
        'profile': profile,
        'image_size_bytes': image_size_bytes,
        'filesystem': str(Path(filesystem).resolve()),
        'filesystem_sha256': digest(filesystem),
    })


def metadata(path):
    sidecar = Path(str(path) + '.uaem')
    if not sidecar.exists():
        return ['----rwed', '']
    # UAE sidecars contain protection, date, time, and an optional comment.
    # Dates are deliberately excluded: rebuilding staging trees changes them.
    fields = sidecar.read_text(encoding='utf-8').rstrip('\r\n').split(' ', 3)
    if len(fields) < 3 or len(fields[0]) != 8:
        raise ValueError(f'Invalid UAE metadata: {sidecar}')
    return [fields[0], fields[3] if len(fields) == 4 else '']


def amiga_component(name):
    # UAE percent escapes are decoded once, so %253f remains literal %3f.
    return re.sub(r'%([0-9a-fA-F]{2})', lambda m: chr(int(m[1], 16)), name)


def amiga_path(relative):
    parts = PurePosixPath(relative).parts
    if len(parts) < 2 or parts[0] not in PARTITIONS:
        raise ValueError(f'Not a payload path: {relative}')
    decoded = [amiga_component(x) for x in parts[1:]]
    if any(not x or x in {'.', '..'} or ':' in x or '/' in x for x in decoded):
        raise ValueError(f'Invalid Amiga payload path: {relative}')
    return parts[0] + ':' + '/'.join(decoded)


def quote(value, pattern=False):
    # Keep shell expansion and control characters out of generated scripts.
    if any(ord(c) < 32 or ord(c) > 255 or c in '$`' for c in value):
        raise ValueError(f'Path requires a full rebuild: {value!r}')
    if pattern:
        value = ''.join("'" + c if c in "#?[]()~|'%*" else c for c in value)
    return '"' + value.replace('*', '**').replace('"', '*"') + '"'


def stat_signature(value):
    return [value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns]


def snapshot(workspace, partitions, cache=None, stats=None, clean=False):
    """Read each node's attributes once; reuse hashes only for identical file identities."""
    workspace = Path(workspace).resolve()
    previous = (cache.get('files', {}) if isinstance(cache, dict) and cache.get('schema') == 1
                and cache.get('workspace') == str(workspace) else {})
    if not isinstance(previous, dict):
        previous = {}
    result, seen, records = {}, {}, {}
    counts = {'hashed_files': 0, 'reused_hashes': 0, 'metadata_reads': 0}

    def walk(directory, prefix):
        with os.scandir(directory) as scan:
            nodes = {node.name: node for node in scan}
        for name in sorted(nodes):
            node = nodes[name]
            if name in IGNORED:
                if clean and name == '.DS_Store' and node.is_file(follow_symlinks=False):
                    os.unlink(node.path)
                continue
            if name.endswith('.uaem'):
                continue
            value = node.stat(follow_symlinks=False)
            is_dir = stat_module.S_ISDIR(value.st_mode)
            if not (is_dir or stat_module.S_ISREG(value.st_mode)):
                raise ValueError(f'Unsupported payload node: {node.path}')
            rel = prefix + '/' + name
            key = amiga_path(rel).casefold()
            if key in seen:
                raise ValueError(f'Amiga filename collision: {seen[key]} and {rel}')
            seen[key] = rel
            signature = stat_signature(value)
            old = previous.get(rel)
            old = old if isinstance(old, list) and len(old) == 4 else None
            sidecar = nodes.get(name + '.uaem')
            if sidecar and not sidecar.is_file(follow_symlinks=False):
                raise ValueError(f'Unsupported UAE metadata node: {sidecar.path}')
            meta_signature = stat_signature(sidecar.stat(follow_symlinks=False)) if sidecar else None
            if old and old[2] == meta_signature and isinstance(old[3], list) and len(old[3]) == 2:
                meta = old[3]
            elif sidecar:
                meta = metadata(Path(node.path))
                counts['metadata_reads'] += 1
                if stat_signature(os.stat(sidecar.path, follow_symlinks=False)) != meta_signature:
                    raise ValueError(f'Metadata changed during comparison: {sidecar.path}')
            else:
                meta = ['----rwed', '']
            entry = {'type': 'dir' if is_dir else 'file', 'metadata': meta}
            content_hash = None
            if not is_dir:
                if old and old[0] == signature and isinstance(old[1], str) and re.fullmatch('[0-9a-f]{64}', old[1]):
                    content_hash = old[1]
                    counts['reused_hashes'] += 1
                else:
                    content_hash = digest(node.path)
                    counts['hashed_files'] += 1
                    if stat_signature(os.stat(node.path, follow_symlinks=False)) != signature:
                        raise ValueError(f'Payload changed during comparison: {node.path}')
                entry.update(size=value.st_size, sha256=content_hash)
            result[rel] = entry
            records[rel] = [signature, content_hash, meta_signature, meta]
            if is_dir:
                walk(node.path, rel)

    for volume, _ in partitions:
        if volume not in PARTITIONS:
            raise ValueError(f'Unsupported incremental partition: {volume}')
        root = workspace / volume
        if root.is_symlink() or not root.is_dir():
            raise ValueError(f'Missing or unsupported staged partition: {root}')
        walk(root, volume)
    if cache is not None:
        cache.clear()
        cache.update(schema=1, workspace=str(workspace), files=records)
    if stats is not None:
        stats.update(counts)
    return result


def changes(previous, current):
    remove = {k for k in previous if k not in current or previous[k] != current[k]}
    copy = {k for k in current if k not in previous or previous[k] != current[k]}
    # Replacing directory metadata/type requires restoring its complete subtree.
    replaced_dirs = [k for k in remove if previous[k]['type'] == 'dir']
    for directory in replaced_dirs:
        copy.update(k for k in current if k.startswith(directory + '/'))
    # One recursive delete covers all removed descendants.
    remove = {k for k in remove if not any(k.startswith(d + '/') for d in replaced_dirs if d != k)}
    return sorted(remove, key=lambda k: (-k.count('/'), k)), sorted(copy)


def payload_sizes(entries, partitions):
    """Estimate allocated bytes from the already-hashed payload, without walking it."""
    sizes = {v: 0 for v, _ in partitions}
    for rel, entry in entries.items():
        volume, name = rel.split('/', 1)
        sizes[volume] += 1 + math.ceil(len(name) / 512) * 512
        if entry['type'] == 'file':
            sizes[volume] += math.ceil(entry['size'] / 512) * 512
    return sizes


def minimum_partitions(entries, partitions):
    """Estimate required PFS cylinders, leaving 4 MiB beyond payload overhead."""
    return [[v, math.ceil(1.05 * size / (512 * 16 * 63)) + 8]
            for v, size in payload_sizes(entries, partitions).items()]


def layout_from_entries(entries, partitions, image_size_bytes, boot_extra_bytes):
    """Choose a layout only for full rebuilds, using the existing content manifest."""
    cylinder = 512 * 16 * 63
    sizes = payload_sizes(entries, partitions)
    layout = [[v, math.ceil((1.05 * (size + (80 if v == 'DH0' else 40) * 1024**2)
                            + (boot_extra_bytes if v == 'DH0' else 0)) / cylinder)]
              for v, size in sizes.items()]
    if image_size_bytes:
        if [v for v, _ in layout] != ['DH0', 'DH1']:
            raise ValueError('Fixed-size images require DH0 and DH1')
        data_cylinders = image_size_bytes // cylinder - 2 - layout[0][1]
        if data_cylinders < layout[1][1]:
            raise ValueError(f'Payload and partition reserves do not fit the {image_size_bytes}-byte image limit')
        layout[1][1] = data_cylinders
    return layout


def image_signature(path):
    s = Path(path).stat()
    return {'size': s.st_size, 'mtime_ns': s.st_mtime_ns, 'ctime_ns': s.st_ctime_ns}


def signature_matches(path, recorded):
    """Metadata-only ctime changes do not imply changed image bytes."""
    if not recorded or not Path(path).is_file():
        return False
    actual = image_signature(path)
    return all(actual.get(k) == recorded.get(k) for k in ('size', 'mtime_ns'))


def baseline_path(image):
    return image_cache_directory(image) / 'baseline.hdf'


def source_image(image, state):
    if not state:
        return None
    baseline = baseline_path(image)
    if signature_matches(baseline, state.get('baseline_signature')):
        return baseline
    if signature_matches(image, state.get('image_signature')):
        return image
    return None


def try_clone(source, target):
    """Only use a cheap filesystem clone for the persistent cached baseline."""
    result = subprocess.run(['cp', '-c', str(source), str(target)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0


def cache_baseline(image, state):
    baseline = baseline_path(image)
    temporary = baseline.with_name('baseline.' + uuid.uuid4().hex + '.tmp')
    before = image_signature(image)
    state.pop('baseline_signature', None)
    try:
        if not try_clone(image, temporary):
            return False
        if image_signature(image) != before:
            raise ValueError('Image changed while caching its clean baseline; retry the build')
        os.replace(temporary, baseline)
        state['baseline_signature'] = image_signature(baseline)
        return True
    finally:
        temporary.unlink(missing_ok=True)


def load_state(path):
    try:
        state = json.loads(Path(path).read_text())
        if not isinstance(state, dict) or state.get('schema') != SCHEMA:
            return None
        if not isinstance(state.get('entries'), dict) or not isinstance(state.get('partitions'), list):
            return None
        for partition in state['partitions']:
            if (not isinstance(partition, list) or len(partition) != 2 or
                    partition[0] not in PARTITIONS or not isinstance(partition[1], int) or partition[1] <= 0):
                return None
        for name, entry in state['entries'].items():
            if (not isinstance(entry, dict) or entry.get('type') not in {'file', 'dir'} or
                    not isinstance(entry.get('metadata'), list) or len(entry['metadata']) != 2):
                return None
            amiga_path(name)
            if entry['type'] == 'file' and (not isinstance(entry.get('size'), int) or
                    entry['size'] < 0 or not re.fullmatch('[0-9a-f]{64}', entry.get('sha256', ''))):
                return None
        return state
    except (OSError, ValueError):
        return None


def reuse_reason(image, state, plan, force=False):
    if force:
        return 'full rebuild requested'
    if state is None:
        return 'no successful-build manifest for the existing image' if image.is_file() else 'no existing image'
    if source_image(image, state) is None:
        return 'existing image changed and no clean cached baseline is available'
    if state.get('profile') != plan['profile'] or state.get('filesystem_sha256') != plan['filesystem_sha256']:
        return 'image profile or PFS filesystem changed'
    if state.get('image_size_bytes', 0) != plan.get('image_size_bytes', 0):
        return 'whole-image size limit changed'
    old = dict(state['partitions'])
    new = dict(plan['minimum_partitions'])
    if old.keys() != new.keys() or any(new[k] > old[k] for k in new):
        return 'partition capacity needs to grow or layout changed'
    return None


def copy_file(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(['cp', '-c', str(source), str(target)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if r.returncode:
        shutil.copy2(source, target)


def stage_delta(workspace, selected):
    root = workspace / 'image-update-delta'
    if root.exists():
        shutil.rmtree(root)
    root.mkdir()
    needed = set(selected)
    for rel in selected:
        needed.update(p.as_posix() for p in PurePosixPath(rel).parents if str(p) != '.')
    for rel in sorted(needed, key=lambda k: (k.count('/'), k)):
        source, target = workspace / rel, root / rel
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            copy_file(source, target)
        sidecar = Path(str(source) + '.uaem')
        if sidecar.is_file():
            copy_file(sidecar, Path(str(target) + '.uaem'))
    return root


def make_script(partitions, remove, copied_volumes, full, token):
    lines = ['Stack 65536', 'Assign T: RAM:', 'FailAt 21', 'Echo "" >RAM:OK']
    def checked(command):
        name, _, arguments = command.partition(' ')
        logged = name + ' >tmp:image-update-command.log ' + arguments
        lines.extend([logged, 'If WARN', f' Echo "FAILED {token}" >tmp:image-update.status',
                      ' UAEquit', ' Quit 20', 'EndIf'])
    if full:
        for volume, _ in partitions:
            lines.append(f'Echo "Formatting {volume}: {PARTITIONS[volume]}..."')
            checked(f'pfsformat drive {volume}: name "{PARTITIONS[volume]}" quick noicons filenamesize=96 <RAM:OK')
    else:
        lines.append(f'Echo "Incremental update: {len(remove)} replaced/deleted paths"')
        for rel in remove:
            checked('tmp:image-update-delete ' + quote(amiga_path(rel), pattern=True) + ' ALL FORCE QUIET')
    for volume in copied_volumes:
        source = f'tmp:{volume}/#?' if full else f'tmp:image-update-delta/{volume}/#?'
        lines.append(f'Echo "Copying {volume}: {"full payload" if full else "changes only"}..."')
        checked(f'Copy {source} {volume}: ALL CLONE QUIET')
    # PFS has delayed writes; the marker must be the final step before UAEquit.
    checked('tmp:image-update-wait 5')
    lines.extend([f'Echo "OK {token}" >tmp:image-update.status', 'UAEquit'])
    return '\n'.join(lines) + '\n'


def image_cache_root():
    # This state must survive normal per-generation build-cache pruning.
    import ags_util
    import ags_paths
    return Path(ags_paths.cache_root()) / 'image-updates'


def image_cache_directory(image):
    identity = hashlib.sha256(os.fsencode(str(Path(image).resolve()))).hexdigest()
    return image_cache_root() / identity


def manifest_path(image):
    return image_cache_directory(image) / 'manifest.json'


def migrate_legacy_manifest(image):
    """Move adjacent bookkeeping into the cache without losing a valid baseline."""
    legacy = Path(str(image) + '.manifest.json')
    target = manifest_path(image)
    if not legacy.is_file():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    cached = load_state(target)
    old = load_state(legacy)
    signature = image_signature(image) if image.exists() else None
    if cached is None or (old and old.get('image_signature') == signature and
                          cached.get('image_signature') != signature):
        temporary = target.with_name('manifest.migrating')
        shutil.copyfile(legacy, temporary)
        os.replace(temporary, target)
    legacy.unlink()


@contextmanager
def image_lock(image):
    directory = image_cache_directory(image)
    directory.mkdir(parents=True, exist_ok=True)
    legacy_path = Path(str(image) + '.build-lock')
    legacy = None
    with (directory / 'build.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Respect an in-flight build started by the previous implementation.
            if legacy_path.exists():
                legacy = legacy_path.open('a')
                fcntl.flock(legacy, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            if legacy:
                legacy.close()
            raise ValueError(f'Another build is updating {image}')
        try:
            yield
        finally:
            if legacy:
                legacy_path.unlink(missing_ok=True)
                legacy.close()


def run(workspace, emulator, force=False):
    workspace = Path(workspace).resolve()
    plan_path = workspace / PLAN_NAME
    if not plan_path.is_file():
        # Explicit legacy full builds retain their existing clone scripts.
        return subprocess.run([emulator, '-f', str(workspace / 'cfg.uae')]).returncode
    plan = json.loads(plan_path.read_text())
    if plan.get('schema') != SCHEMA:
        raise ValueError('Unknown image-update plan version; prepare the build again')
    image = Path(plan['image'])
    image.parent.mkdir(parents=True, exist_ok=True)
    with image_lock(image):
        return update_locked(workspace, image, plan, emulator, force)


def update_locked(workspace, image, plan, emulator, force):
    migrate_legacy_manifest(image)
    state_path = manifest_path(image)
    state = load_state(state_path)
    initial_signature = image_signature(image) if image.exists() else None
    if (state and signature_matches(image, state.get('image_signature')) and
            not signature_matches(baseline_path(image), state.get('baseline_signature'))):
        if cache_baseline(image, state):
            atomic_json(state_path, state)
    print('Comparing staged payload...', flush=True)
    scan_path = image_cache_directory(image) / 'scan-cache.json'
    try:
        scan_cache = json.loads(scan_path.read_text())
        if not isinstance(scan_cache, dict):
            scan_cache = {}
    except (OSError, ValueError):
        scan_cache = {}
    scan_stats = {}
    start = perf_counter()
    current = snapshot(workspace, plan['partitions'], scan_cache, scan_stats, clean=True)
    atomic_json(scan_path, scan_cache)
    del scan_cache
    print(f" > {scan_stats['reused_hashes']} file hashes reused, {scan_stats['hashed_files']} files hashed "
          f"in {perf_counter() - start:.2f}s", flush=True)
    plan['minimum_partitions'] = minimum_partitions(current, plan['partitions'])
    reason = reuse_reason(image, state, plan, force)
    remove, selected = changes(state['entries'], current) if reason is None else ([], sorted(current))
    if reason is None:
        try:
            # Literal filenames are passed to Delete as escaped AmigaDOS patterns.
            for rel in remove:
                quote(amiga_path(rel), pattern=True)
        except ValueError as error:
            reason = str(error)
            remove, selected = [], sorted(current)
    if reason is None and not remove and not selected:
        if not signature_matches(image, state.get('image_signature')):
            restored = image.with_name('.' + image.name + '.' + uuid.uuid4().hex + '.restoring')
            try:
                copy_file(source_image(image, state), restored)
                if (image_signature(image) if image.exists() else None) != initial_signature:
                    raise ValueError('Output image changed during restoration; refusing to replace it')
                os.replace(restored, image)
                state['image_signature'] = image_signature(image)
                atomic_json(state_path, state)
            finally:
                restored.unlink(missing_ok=True)
            print('Restored clean cached HDF; skipping Amiberry.', flush=True)
        else:
            print('HDF is already current; skipping Amiberry.', flush=True)
        return 0
    full = reason is not None
    if full and plan.get('deferred_layout'):
        plan['partitions'] = layout_from_entries(
            current, plan['partitions'], plan.get('image_size_bytes', 0), plan.get('boot_extra_bytes', 0))
    print(('Full rebuild: ' + reason) if full else
          f'Incremental clone: {len(selected)} added/changed entries; {len(remove)} replaced/deleted paths.', flush=True)
    token = uuid.uuid4().hex
    candidate = image.with_name('.' + image.name + '.' + token + '.building')
    target = workspace / 'target.hdf'
    status = workspace / 'image-update.status'
    status.unlink(missing_ok=True)
    try:
        if full:
            # Import util first: existing filesystem helpers have a circular import.
            import ags_util
            from ags_fs import build_pfs
            build_pfs(str(candidate), str(workspace), True, partitions=list(map(tuple, plan['partitions'])))
            allocated = plan['partitions']
            volumes = [v for v, _ in allocated if any(k.startswith(v + '/') for k in current)]
        else:
            copy_file(source_image(image, state), candidate)
            stage_delta(workspace, selected)
            allocated = state['partitions']
            volumes = sorted({PurePosixPath(k).parts[0] for k in selected})
        target.unlink(missing_ok=True)
        target.symlink_to(candidate)
        wait = workspace / 'DH0/C/Wait'
        if not wait.is_file():
            raise ValueError('Staged DH0:C/Wait is required to flush PFS writes')
        shutil.copyfile(wait, workspace / 'image-update-wait')
        delete = workspace / 'DH0/C/Delete'
        if not delete.is_file():
            raise ValueError('Staged DH0:C/Delete is required for incremental updates')
        shutil.copyfile(delete, workspace / 'image-update-delete')
        repo = Path(__file__).resolve().parent.parent
        shutil.copyfile(repo / 'data/cloner/boot.adf', workspace / 'boot.adf')
        (workspace / 'clone').write_text(make_script(allocated, remove, volumes, full, token), encoding='latin-1')
        host_log = workspace / 'amiberry-clone-host.log'
        with host_log.open('w') as log:
            result = subprocess.run([emulator, '-f', str(workspace / 'cfg.uae')],
                                    stdout=log, stderr=subprocess.STDOUT)
        if result.returncode or not status.is_file() or status.read_text().strip() != 'OK ' + token:
            details_path = workspace / 'image-update-command.log'
            details = details_path.read_text(encoding='latin-1').strip() if details_path.exists() else ''
            raise ValueError(f'Amiberry did not confirm a successful clone; the previous HDF is unchanged. {details} See {host_log}')
        if (image_signature(image) if image.exists() else None) != initial_signature:
            raise ValueError('Output image changed during cloning; refusing to replace it')
        limit = plan.get('image_size_bytes', 0)
        if limit and candidate.stat().st_size > limit:
            raise ValueError('Candidate exceeds the whole-image size limit; previous HDF is unchanged')
        with candidate.open('rb') as f:
            os.fsync(f.fileno())
        # Commit image first. A crash before manifest publication invalidates the
        # previous signature and causes a full rebuild on the next attempt.
        os.replace(candidate, image)
        published = {
            'schema': SCHEMA, 'profile': plan['profile'],
            'image': str(image.resolve()),
            'filesystem_sha256': plan['filesystem_sha256'],
            'partitions': allocated, 'image_signature': image_signature(image),
            'image_size_bytes': plan.get('image_size_bytes', 0),
            'entries': current,
        }
        cache_baseline(image, published)
        atomic_json(state_path, published)
        print('Published HDF and successful-build manifest: ' + str(image), flush=True)
        return 0
    finally:
        candidate.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        if image.exists():
            target.symlink_to(image)


def clear_cache(image):
    """Remove one image's retained update data, respecting the updater lock."""
    image = Path(image).resolve()
    with image_lock(image):
        directory = image_cache_directory(image)
        names = {'baseline.hdf', 'manifest.json', 'scan-cache.json'}
        removed = 0
        for path in directory.iterdir():
            if path.name in names or (path.name.startswith('baseline.') and path.suffix == '.tmp'):
                removed += path.stat().st_size
                path.unlink()
    # Leave the zero-byte lock inode in place to keep concurrent locking safe.
    print(f'Removed retained image-update cache for {image} ({removed:,} logical bytes)', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace')
    parser.add_argument('--emulator')
    parser.add_argument('--clear-cache-for', metavar='IMAGE', help='Remove retained update data for this image without building')
    parser.add_argument('--full', action='store_true', help='Force a complete rebuild')
    args = parser.parse_args()
    if not args.clear_cache_for and (not args.workspace or not args.emulator):
        parser.error('--workspace and --emulator are required for a build')
    try:
        if args.clear_cache_for:
            clear_cache(args.clear_cache_for)
            return 0
        return run(args.workspace, args.emulator, args.full)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print('Image update failed: ' + str(error), flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
