#!/usr/bin/env python3
"""Experimental native-chipset Emu68 SD image packager (no gameplay emulation)."""
import argparse
from datetime import date
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import struct
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

from user_paths import normalize_path
from artifact_checksums import write_checksums

ROOT = Path(__file__).resolve().parent.parent
REV = '64839e73a2e9bc694abfa7a3008129296cf8b194'
ASSETS = {
    'hdf2emu68-source.zip': (f'https://github.com/PiStorm/hdf2emu68/archive/{REV}.zip', 'bcab2c71359fca0e3c9a3cbc7a1b5729f1aeb3660a2d2f018c8ace0994943fa7'),
    'Emu68-pistorm32lite.zip': ('https://github.com/michalsc/Emu68/releases/download/v1.0.7/Emu68-pistorm32lite.zip', '34d4c3a0c4f39afa5846c933c1074bf712b18fe4e9e9b36e16de63bd574f9a12'),
    'Emu68-pistorm.zip': ('https://github.com/michalsc/Emu68/releases/download/v1.0.7/Emu68-pistorm.zip', '12f1b961e0063f3fe8ebd3e10a837f50f547225962f38fb9918fe96bdd7b1fa4'),
    'WHDLoadWrapper020.lha': ('https://drive.google.com/uc?export=download&id=1IhaKPNeqsyfrXVjIK8Ixv82IvAPjb5Iu', 'a8189c40e7940303ca6d85dcda49375693ac20a86feb8f6f010c93b11e0f2cd6'),
}


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def asset(cache, name):
    path = cache / name
    url, expected = ASSETS[name]
    if not path.exists():
        partial = path.with_suffix('.download')
        try:
            urllib.request.urlretrieve(url, partial)
            if sha(partial) != expected:
                raise ValueError(f'Checksum mismatch: {name}')
            partial.replace(path)
        finally:
            partial.unlink(missing_ok=True)
    if sha(path) != expected:
        raise ValueError(f'Checksum mismatch: {path}; remove it and retry')
    return path


def unzip(path, dest):
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            p = PurePosixPath(info.filename)
            if p.is_absolute() or '..' in p.parts or (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError(f'Unsafe ZIP entry: {p}')
        z.extractall(dest)


def wrapper_overlay(archive, dest):
    import lhafile
    lha = lhafile.Lhafile(str(archive))
    for name in lha.namelist():
        p = PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts:
            raise ValueError(f'Unsafe LHA entry: {name}')
        parts = p.parts[1:]
        if not parts:
            continue
        if parts[0] in ('C', 'S'):
            relative = Path(*parts)
        elif parts[0] in ('DB', 'DB-General'):
            relative = Path('S/WHDLoad-Wrapper', *parts[1:])
        elif parts == ('ReadMe',):
            relative = Path('S/WHDLoad-Wrapper/ReadMe')
        else:
            continue
        target = dest / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(lha.read(name))
    shutil.copyfile(dest / 'C/WHDLoadWrapper', dest / 'C/WHDLoad')
    scripts = dest / 'S/WHDLoad-Wrapper'
    shutil.copyfile(scripts / 'StartupScript_NoScreenText', scripts / 'StartupScript')
    (scripts / 'Updater/WHDUpdate.conf').write_text('DisableOnlineChecks=1\n')


def patch_hdf(args, work, candidate):
    # Always patch a private copy; never attach the source image writable.
    cloned = False
    if os.uname().sysname == 'Darwin':
        cloned = subprocess.run(['cp', '-c', str(args.hdf), str(candidate)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    if not cloned:
        shutil.copyfile(args.hdf, candidate)
    overlay = work / 'overlay'
    wrapper_overlay(asset(args.cache, 'WHDLoadWrapper020.lha'), overlay)
    shutil.copyfile(ROOT / 'data/cloner/boot.adf', work / 'boot.adf')
    (work / 'target.hdf').symlink_to(candidate)
    config = (ROOT / 'data/cloner/template.uae').read_text()
    for key, value in {'AVSTEMP': work, 'AVSCONTENT': os.environ.get('AVSCONTENT', ''), 'KICKSTART_ROM': args.rom}.items():
        config = config.replace('$' + key, str(value))
    (work / 'cfg.uae').write_text(config)
    lines = ['Stack 65536', 'Assign T: RAM:', 'FailAt 21',
             'If EXISTS DH0:C/WHDLoad.ori', ' Echo "Already wrapped" >tmp:status', ' UAEquit', ' Quit 20', 'EndIf']
    def checked(command):
        name, _, arguments = command.partition(' ')
        lines.extend([name + ' >tmp:command.log ' + arguments, 'If WARN', f' Echo "FAILED: {command}" >tmp:status', ' UAEquit', ' Quit 20', 'EndIf'])
    checked('Copy DH0:C/Wait tmp:wait')
    checked('DH0:C/Rename DH0:C/WHDLoad DH0:C/WHDLoad.ori')
    for library in ('68040.library', '68060.library', '680x0.library'):
        lines.append(f'If EXISTS DH0:Libs/{library}')
        checked(f'DH0:C/Rename DH0:Libs/{library} DH0:Libs/{library}.disabled-pistorm')
        lines.append('EndIf')
    checked('Copy tmp:overlay/#? DH0: ALL CLONE QUIET')
    checked('Copy DH0:C/WHDLoad tmp:installed-wrapper')
    # The filesystem batches writes. Flush before reporting success and quitting.
    checked('tmp:wait 5')
    lines.extend(['Echo "OK" >tmp:status', 'UAEquit'])
    (work / 'clone').write_text('\n'.join(lines) + '\n', encoding='latin1')
    print('Installing PiStorm overlay with the Amiberry filesystem cloner...', flush=True)
    try:
        with (work / 'amiberry.log').open('w') as log:
            subprocess.run([str(args.amiberry), '-f', str(work / 'cfg.uae'), '--log'], stdout=log, stderr=subprocess.STDOUT, check=True, timeout=300)
        if not (work / 'status').exists() or (work / 'status').read_text().strip() != 'OK':
            raise ValueError('Amiberry did not confirm overlay installation')
        if sha(work / 'installed-wrapper') != sha(overlay / 'C/WHDLoad'):
            raise ValueError('Installed WHDLoadWrapper verification failed')
    except Exception:
        log_path = args.output.with_suffix('.build.log')
        shutil.copyfile(work / 'amiberry.log', log_path)
        for name in ('status', 'command.log'):
            if (work / name).exists():
                print(name + ': ' + (work / name).read_text(encoding='latin1'), flush=True)
        print(f'Cloner log saved to {log_path}', flush=True)
        raise


def validate(image, hdf, boot):
    """Independently verify MBR, embedded RDB image and every FAT32 boot file."""
    with image.open('r+b') as f:
        mbr = f.read(512)
        if mbr[510:] != b'\x55\xaa':
            raise ValueError('Invalid MBR signature')
        parts = [struct.unpack_from('<B3sB3sII', mbr, 446 + i * 16) for i in range(2)]
        fat, amiga = parts
        if fat[2] != 0x0c or amiga[2] != 0x76 or fat[4] != 2048 or fat[4] + fat[5] > amiga[4]:
            raise ValueError('Invalid Emu68 partition layout')
        if hdf.stat().st_size > amiga[5] * 512:
            raise ValueError('Embedded HDF exceeds partition')
        # Converter stops at EOF of HDF; extend the final sector to the MBR boundary.
        expected_size = (amiga[4] + amiga[5]) * 512
        if image.stat().st_size > expected_size:
            raise ValueError('Unexpected data beyond image partitions')
        f.truncate(expected_size)
        f.seek(amiga[4] * 512)
        remaining, digest = hdf.stat().st_size, hashlib.sha256()
        while remaining:
            data = f.read(min(1024 * 1024, remaining))
            if not data:
                raise ValueError('Truncated HDF')
            digest.update(data)
            remaining -= len(data)
        if digest.hexdigest() != sha(hdf):
            raise ValueError('Embedded HDF differs from patched source')
        base = fat[4] * 512
        f.seek(base)
        bpb = f.read(512)
        sector = struct.unpack_from('<H', bpb, 11)[0]
        cluster_sectors = bpb[13]
        reserved = struct.unpack_from('<H', bpb, 14)[0]
        fats = bpb[16]
        fat_sectors = struct.unpack_from('<I', bpb, 36)[0]
        root = struct.unpack_from('<I', bpb, 44)[0]
        if sector != 512 or not cluster_sectors or bpb[510:] != b'\x55\xaa' or not fat_sectors:
            raise ValueError('Invalid FAT32 boot sector')
        fat_start = base + reserved * sector
        data_start = fat_start + fats * fat_sectors * sector
        def chain(cluster):
            seen, data = set(), bytearray()
            while 2 <= cluster < 0x0ffffff8:
                if cluster in seen or cluster >= fat_sectors * sector // 4:
                    raise ValueError('Invalid FAT chain')
                seen.add(cluster)
                offset = data_start + (cluster - 2) * cluster_sectors * sector
                if offset + cluster_sectors * sector > (fat[4] + fat[5]) * 512:
                    raise ValueError('FAT cluster outside partition')
                f.seek(offset)
                data.extend(f.read(cluster_sectors * sector))
                f.seek(fat_start + cluster * 4)
                cluster = struct.unpack('<I', f.read(4))[0] & 0x0fffffff
            return data
        entries, names = {}, {}
        for off in range(0, len(directory := chain(root)), 32):
            entry = directory[off:off + 32]
            if entry[0] == 0:
                break
            if entry[0] == 0xe5:
                names = {}
                continue
            if entry[11] == 0x0f:
                names[entry[0] & 31] = bytes(entry[1:11] + entry[14:26] + entry[28:32]).decode('utf-16le')
                continue
            short = entry[:8].decode('ascii').rstrip() + ('.' + entry[8:11].decode('ascii').rstrip() if entry[8:11].strip() else '')
            name = ''.join(names[k] for k in sorted(names)).split('\0')[0].rstrip('\uffff') if names else short
            names = {}
            if entry[11] & 0x18:
                continue
            cluster = struct.unpack_from('<H', entry, 26)[0] | struct.unpack_from('<H', entry, 20)[0] << 16
            size = struct.unpack_from('<I', entry, 28)[0]
            entries[name.casefold()] = bytes(chain(cluster)[:size])
        for path in boot.iterdir():
            if not path.is_file() or entries.get(path.name.casefold()) != path.read_bytes():
                raise ValueError(f'Boot file missing or corrupt: {path.name}')
    print(f'Validated all boot files and embedded HDF; image size {expected_size:,} bytes.', flush=True)


def prepare_converter_source(source):
    """Apply the small POSIX and type fixes to the pinned upstream source."""
    path = source / 'hdf2emu68.c'
    text = path.read_text()
    fixes = (
        (r'%s\\%s', '%s/%s', 2),
        ('if (f=fopen(pp, "rb"))', 'if ((f = fopen(pp, "rb")) != NULL)', 1),
        ('int w;', 'UINT w;', 2),
    )
    for old, new, count in fixes:
        if text.count(old) != count:
            raise ValueError(f'Unexpected pinned converter source: {old!r}')
        text = text.replace(old, new)
    path.write_text(text)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model', choices=('pistorm', 'pistorm32lite'), default='pistorm32lite')
    p.add_argument('--hdf', type=Path, required=True)
    p.add_argument('--rom', type=Path, required=True)
    p.add_argument('--output', type=Path, help='Optional explicit artifact filename')
    p.add_argument('--output-dir', type=Path, help='Directory selected by run_distros.sh; defaults to DISTRO_OUT or AVSDEST/distros')
    p.add_argument('--date-stamp', default=os.environ.get('DISTRO_DATE', date.today().strftime('%Y.%m.%d')))
    p.add_argument('--amiberry', type=Path, required=True)
    p.add_argument('--cache', type=Path, default=ROOT / 'data/cache/pistorm')
    args = p.parse_args()
    default_output_dir = os.environ.get('DISTRO_OUT', str(Path(os.environ.get('AVSDEST', str(Path.home() / 'Developer/AV-Output'))) / 'distros'))
    output_dir = Path(normalize_path(args.output_dir or (Path(normalize_path(args.output)).parent if args.output else default_output_dir)))
    variant = 'PiStormECS' if args.model == 'pistorm' else 'PiStormAGA'
    if not args.output:
        output_dir = output_dir / f'AmigaVision-{variant}'
    filename = Path(normalize_path(args.output)).name if args.output else f'AmigaVision-{variant}-{args.date_stamp}.img.xz'
    args.output = output_dir / filename
    for key in ('hdf', 'rom', 'output', 'amiberry', 'cache'):
        setattr(args, key, getattr(args, key).expanduser().resolve())
    if args.output in (args.hdf, args.rom) or not str(args.output).endswith('.img.xz'):
        p.error('Output must be a separate .img.xz file')
    for path in (args.hdf, args.rom, args.amiberry):
        if not path.is_file():
            p.error(f'Required file missing: {path}')
    with args.hdf.open('rb') as f:
        if f.read(4) != b'RDSK':
            p.error('Source must be a whole RDB HDF')
    if args.rom.stat().st_size not in (256 * 1024, 512 * 1024, 1024 * 1024):
        p.error('Expected a raw Kickstart ROM (256/512/1024 KiB)')
    args.cache.mkdir(parents=True, exist_ok=True)
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        p.error(f"Cannot create output directory {args.output.parent}: {exc.strerror}")
    # Work alongside output for APFS clones and atomic final publication.
    with tempfile.TemporaryDirectory(prefix='.pistorm-', dir=args.output.parent) as tmp:
        work = Path(tmp)
        boot = work / 'boot'
        unzip(asset(args.cache, f'Emu68-{args.model}.zip'), boot)
        shutil.copyfile(args.rom, boot / 'kick.rom')
        unzip(asset(args.cache, 'hdf2emu68-source.zip'), work / 'converter')
        source = work / 'converter' / f'hdf2emu68-{REV}'
        prepare_converter_source(source)
        converter = work / 'hdf2emu68'
        # Upstream omits POSIX includes/stricmp mapping and the Unicode object.
        subprocess.run(['cc', '-include', 'sys/stat.h', '-include', 'strings.h', '-Dstricmp=strcasecmp', str(source / 'hdf2emu68.c'), str(source / 'fatfs/diskio.c'), str(source / 'fatfs/ff.c'), str(source / 'fatfs/ffunicode.c'), '-I', str(source / 'fatfs'), '-O3', '-o', str(converter)], check=True)
        candidate = work / 'patched.hdf'
        patch_hdf(args, work, candidate)
        image = work / 'prototype.img'
        print('Creating Emu68 SD image...', flush=True)
        subprocess.run([str(converter), str(candidate), '-fatsize', '64', '-fatdir', str(boot), '-output', str(image)], check=True)
        validate(image, candidate, boot)
        candidate.unlink()
        print('Compressing prototype image...', flush=True)
        subprocess.run(['xz', '-T0', '-1', '-v', str(image)], check=True,
                       env=dict(os.environ, TMPDIR=str(work), TMP=str(work), TEMP=str(work)))
        compressed = image.with_suffix('.img.xz')
        compressed.replace(args.output)
    checksums = write_checksums(args.output)
    checksum = checksums['sha256']
    md5_checksum = checksums['md5']
    print(f'Created {args.output}\nSHA256 {checksum}\nMD5 {md5_checksum}\nPrototype: hardware testing required.')


if __name__ == '__main__':
    main()
