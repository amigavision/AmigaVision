"""Byte-preserving native base staging and comparison (host mtimes are not identity)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

IGNORED = {'.DS_Store', 'Thumbs.db', '__MACOSX', '.git', '.gitignore', '.gitattributes'}

def ignored_name(name):
    return name.startswith('.') or name in IGNORED

def ignore_host_files(directory, names):
    return [name for name in names if ignored_name(name)]

def remove_host_files(root):
    for current, dirs, files in os.walk(root):
        for name in dirs[:]:
            if ignored_name(name):
                shutil.rmtree(Path(current) / name)
                dirs.remove(name)
        for name in files:
            if ignored_name(name):
                # macOS may remove AppleDouble sidecars along with their file.
                (Path(current) / name).unlink(missing_ok=True)

def file_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def tree_manifest(root):
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError(f'Not a native base directory: {root}')
    result = {}
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(x for x in dirs if not ignored_name(x))
        for name in sorted(dirs + [x for x in files if not ignored_name(x)]):
            p = Path(current) / name
            if p.is_symlink() or not (p.is_dir() or p.is_file()):
                raise ValueError(f'Unsupported special file or symlink: {p}')
            result[p.relative_to(root).as_posix()] = (
                {'type': 'directory'} if p.is_dir() else
                {'type': 'file', 'size': p.stat().st_size, 'sha256': file_hash(p)})
    return result

def directory_fingerprint(root):
    encoded = json.dumps(tree_manifest(root), sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(encoded).hexdigest()

def stage_directory(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination or source in destination.parents or destination in source.parents:
        raise ValueError('Source and staging directory must be separate trees')
    tree_manifest(source)  # Reject symlinks/special files before copying anything.
    if destination.exists():
        raise ValueError(f'Staging destination must not exist: {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Never hardlink to the versioned source: build overlays may modify staged files.
    if os.name == 'posix':
        destination.mkdir()
        entries = [str(p) for p in source.iterdir() if not ignored_name(p.name)]
        if not entries:
            return
        # Avoid macOS metadata copies (AppleDouble files on exFAT). Cloning may
        # fail across filesystems, in which case use the portable copy below.
        options = '-cRX' if sys.platform == 'darwin' else '-cR'
        result = subprocess.run(['cp', options, *entries, str(destination)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            remove_host_files(destination)
            return
        shutil.rmtree(destination)
    # copy2 also copies extended attributes, recreating macOS sidecars on exFAT.
    # Amiga metadata lives in the .uaem files and is copied as ordinary data.
    shutil.copytree(source, destination, ignore=ignore_host_files,
                    copy_function=shutil.copy)
    remove_host_files(destination)

def compare(left, right):
    a, b = tree_manifest(left), tree_manifest(right)
    return {'left_only': sorted(a.keys() - b.keys()),
            'right_only': sorted(b.keys() - a.keys()),
            'changed': sorted(k for k in a.keys() & b.keys() if a[k] != b[k])}

def verify_hdf(image, directory):
    """Check native files and every .uaem directly against a read-only FFS image."""
    from amitools.fs.blkdev.BlkDevFactory import BlkDevFactory
    from amitools.fs.ADFSVolume import ADFSVolume
    # Upstream name for the .uaem metadata format also used by Amiberry.
    from amitools.fs.MetaInfoFSUAE import MetaInfoFSUAE
    from amitools.fs.MetaDB import MetaDB
    before = file_hash(image)
    expected, file_count, byte_count = {}, 0, 0
    dev = BlkDevFactory().open(str(image), read_only=True)
    try:
        volume = ADFSVolume(dev)
        volume.open()
        metadata = MetaInfoFSUAE()
        # The volume metadata and geometry are siblings of the mounted directory.
        volume_meta = MetaDB()
        volume_meta.set_volume_name(volume.name.get_unicode())
        volume_meta.set_root_meta_info(volume.get_meta_info())
        volume_meta.set_dos_type(volume.boot.dos_type)
        with tempfile.TemporaryDirectory(prefix='av-root-metadata-') as temp:
            expected_meta = Path(temp)/'volume.xdfmeta'
            volume_meta.save(str(expected_meta))
            actual_meta = Path(str(directory)+'.xdfmeta')
            volume_metadata_matches = actual_meta.is_file() and actual_meta.read_bytes() == expected_meta.read_bytes()
        actual_geometry = Path(str(directory)+'.blkdev')
        expected_geometry = dev.get_chs_str()+'\n'+dev.get_block_size_str()+'\n'
        geometry_matches = actual_geometry.is_file() and actual_geometry.read_bytes() == expected_geometry.encode()
        actual_bootcode = Path(str(directory)+'.bootcode')
        bootcode_matches = (actual_bootcode.is_file() and actual_bootcode.read_bytes() == volume.boot.boot_code
                            if volume.boot.boot_code is not None else not actual_bootcode.exists())
        def walk(node, prefix=''):
            nonlocal file_count, byte_count
            for entry in node.get_entries():
                name = prefix + entry.name.get_unicode_name()
                raw = metadata.generate_data(entry.meta_info).encode('utf-8')
                expected[name + '.uaem'] = {'type': 'file', 'size': len(raw),
                                           'sha256': hashlib.sha256(raw).hexdigest()}
                if entry.is_dir():
                    expected[name] = {'type': 'directory'}
                    walk(entry, name + '/')
                elif entry.is_file():
                    data = entry.get_file_data()
                    expected[name] = {'type': 'file', 'size': len(data),
                                      'sha256': hashlib.sha256(data).hexdigest()}
                    file_count += 1
                    byte_count += len(data)
                else:
                    raise ValueError(f'Unsupported Amiga node: {name}')
                entry.flush()
        walk(volume.get_root_dir())
    finally:
        dev.close()
    actual = tree_manifest(directory)
    result = {'source_sha256': before, 'source_unchanged': before == file_hash(image),
              'amiga_files': file_count, 'amiga_bytes': byte_count,
              'volume_metadata_matches': volume_metadata_matches,
              'geometry_matches': geometry_matches, 'bootcode_matches': bootcode_matches,
              'expected_entries_including_sidecars': len(expected),
              'missing': sorted(expected.keys() - actual.keys()),
              'extra': sorted(actual.keys() - expected.keys()),
              'changed': sorted(k for k in expected.keys() & actual.keys() if expected[k] != actual[k])}
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('compare'); p.add_argument('left'); p.add_argument('right')
    p = sub.add_parser('verify-hdf'); p.add_argument('image'); p.add_argument('directory')
    for p in sub.choices.values():
        p.add_argument('--report', help='Save machine-readable results')
    args = parser.parse_args()
    result = compare(args.left, args.right) if args.action == 'compare' else verify_hdf(args.image, args.directory)
    output = json.dumps(result, indent=2, sort_keys=True)
    if args.report:
        Path(args.report).write_text(output + '\n')
    print(output)
    bad = any(result.get(k) for k in ['left_only', 'right_only', 'changed', 'missing', 'extra'])
    if any(result.get(k) is False for k in ['source_unchanged', 'volume_metadata_matches', 'geometry_matches', 'bootcode_matches']):
        bad = True
    return int(bad)

if __name__ == '__main__':
    raise SystemExit(main())
