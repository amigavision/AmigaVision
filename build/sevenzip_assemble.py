"""Join independent 7z blocks without recompression or archive rewrites.

Inputs are our own `7zz a -ms=off -mhc=off` archives. Other layouts fail
closed. Format reference: https://www.7-zip.org/7z.html and 7-Zip's
DOC/7zFormat.txt. Compression and extraction remain handled by 7-Zip.
"""
import os
from pathlib import Path, PurePosixPath
import struct
import zlib

SIGNATURE = b'7z\xbc\xaf\x27\x1c\x00\x04'
MAX_HEADER = 64 * 1024 * 1024


class Reader:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def take(self, count):
        if count < 0 or self.pos + count > len(self.data):
            raise ValueError('Truncated 7z metadata')
        value = self.data[self.pos:self.pos + count]
        self.pos += count
        return value

    def byte(self):
        return self.take(1)[0]

    def expect(self, value):
        if self.byte() != value:
            raise ValueError(f'Unsupported 7z layout; expected property {value:#x}')

    def number(self):
        first, value = self.byte(), 0
        for count in range(8):
            mask = 0x80 >> count
            if not first & mask:
                return value | ((first & (mask - 1)) << (8 * count))
            value |= self.byte() << (8 * count)
        return value

    def count(self):
        count = self.number()
        if count > 1000000:
            raise ValueError('Excessive 7z metadata count')
        return count

    def bits(self, count):
        data = self.take((count + 7) // 8)
        return [bool(data[i // 8] & (0x80 >> (i % 8))) for i in range(count)]

    def digests(self, count):
        defined = [True] * count if self.byte() else self.bits(count)
        return [self.take(4) if yes else None for yes in defined]

    def end(self):
        if self.pos != len(self.data):
            raise ValueError('Trailing 7z metadata')


def number(value):
    if not 0 <= value < 1 << 64:
        raise ValueError('7z integer out of range')
    for count in range(8):
        if value < 1 << (7 + 7 * count):
            first = (0xff << (8 - count)) & 0xff if count else 0
            return bytes([first | (value >> (8 * count))]) + value.to_bytes(8, 'little')[:count]
    return b'\xff' + struct.pack('<Q', value)


def bits(values):
    result = bytearray((len(values) + 7) // 8)
    for i, yes in enumerate(values):
        if yes:
            result[i // 8] |= 0x80 >> (i % 8)
    return bytes(result)


def defined_values(values, external=False):
    defined = [value is not None for value in values]
    mask = b'\x01' if all(defined) else b'\x00' + bits(defined)
    return mask + (b'\x00' if external else b'') + b''.join(v for v in values if v is not None)


def read_folder(reader):
    start = reader.pos
    ins = outs = 0
    for _ in range(reader.count()):
        flags = reader.byte()
        if flags & 0xc0:
            raise ValueError('Unsupported 7z coder flags')
        codec = reader.take(flags & 15)
        if codec == b'\x06\xf1\x07\x01':
            raise ValueError('Encrypted archives are not supported')
        if flags & 0x10:
            inputs, outputs = reader.count(), reader.count()
        else:
            inputs = outputs = 1
        ins += inputs
        outs += outputs
        if flags & 0x20:
            reader.take(reader.number())
    if not 0 < outs <= 32 or ins - (outs - 1) != 1:
        raise ValueError('Expected one packed stream per independent folder')
    for _ in range(outs - 1):
        if reader.number() >= ins or reader.number() >= outs:
            raise ValueError('Invalid 7z coder binding')
    return reader.data[start:reader.pos], outs


def read_archive(path, renames):
    path = Path(path)
    with path.open('rb') as source:
        signature = source.read(32)
        if len(signature) != 32 or signature[:8] != SIGNATURE:
            raise ValueError('Unsupported 7z signature/version')
        if zlib.crc32(signature[12:]) != struct.unpack_from('<I', signature, 8)[0]:
            raise ValueError('Invalid 7z start-header CRC')
        offset, size, crc = struct.unpack_from('<QQI', signature, 12)
        if size > MAX_HEADER or 32 + offset + size != path.stat().st_size:
            raise ValueError('Invalid 7z header bounds')
        source.seek(32 + offset)
        data = source.read(size)
        if zlib.crc32(data) != crc:
            raise ValueError('Invalid 7z metadata CRC')
    reader = Reader(data)
    reader.expect(1)
    packed, folders, sizes, digests = [], [], [], []
    kind = reader.byte()
    if kind == 4:
        kind = reader.byte()
        if kind == 6:
            if reader.number() != 0:
                raise ValueError('Expected contiguous 7z packed streams')
            count = reader.count()
            reader.expect(9)
            packed = [reader.number() for _ in range(count)]
            kind = reader.byte()
            if kind == 10:
                reader.digests(count)  # Unpacked CRCs below remain authoritative.
                kind = reader.byte()
            if kind != 0:
                raise ValueError('Unsupported 7z PackInfo')
            kind = reader.byte()
        if kind == 7:
            reader.expect(11)
            count = reader.count()
            reader.expect(0)
            records = [read_folder(reader) for _ in range(count)]
            folders = [raw for raw, _ in records]
            reader.expect(12)
            sizes = [[reader.number() for _ in range(outs)] for _, outs in records]
            kind = reader.byte()
            digests = reader.digests(count) if kind == 10 else [None] * count
            if kind == 10:
                kind = reader.byte()
            if kind != 0:
                raise ValueError('Unsupported 7z UnPackInfo')
            kind = reader.byte()
        if len(packed) != len(folders):
            raise ValueError('Expected independent, non-solid 7z folders')
        if kind == 8:
            kind = reader.byte()
            if kind == 13:
                if any(reader.number() != 1 for _ in folders):
                    raise ValueError('Solid 7z inputs are not supported')
                kind = reader.byte()
            if kind == 10:
                missing = [i for i, value in enumerate(digests) if value is None]
                for i, value in zip(missing, reader.digests(len(missing))):
                    digests[i] = value
                kind = reader.byte()
            if kind != 0:
                raise ValueError('Unsupported 7z SubStreamsInfo')
            kind = reader.byte()
        if kind != 0:
            raise ValueError('Unsupported 7z streams metadata')
        kind = reader.byte()
    if kind != 5:
        raise ValueError('Expected plain 7z FilesInfo (-mhc=off)')
    count = reader.count()
    properties = {}
    while kind := reader.byte():
        if kind == 25:  # Alignment padding can appear more than once.
            reader.take(reader.number())
            continue
        if kind in properties:
            raise ValueError(f'Duplicate 7z property {kind:#x} at {reader.pos} in {path}')
        properties[kind] = reader.take(reader.number())
    reader.expect(0)
    reader.end()
    empty_reader = Reader(properties.get(14, b''))
    empty = empty_reader.bits(count) if 14 in properties else [False] * count
    empty_count = sum(empty)
    files = Reader(properties.get(15, b'')).bits(empty_count) if 15 in properties else [False] * empty_count
    anti = Reader(properties.get(16, b'')).bits(empty_count) if 16 in properties else [False] * empty_count
    if any(anti):
        raise ValueError('7z anti-items are not supported')
    names = Reader(properties.pop(17, b''))
    names.expect(0)
    decoded = names.take(len(names.data) - names.pos).decode('utf-16le').split('\0')
    if len(decoded) != count + 1 or decoded[-1] != '':
        raise ValueError('Invalid 7z filenames')
    missing = set(renames) - set(decoded[:-1])
    if missing:
        raise ValueError(f'Renamed 7z members are missing: {sorted(missing)}')
    entries, empty_index = [], 0
    for i, name in enumerate(decoded[:-1]):
        name = renames.get(name, name)
        if not name or '\\' in name or PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts:
            raise ValueError(f'Unsafe archive path: {name!r}')
        row = {'name': name, 'empty': empty[i], 'file': files[empty_index] if empty[i] else False}
        empty_index += int(empty[i])
        entries.append(row)
    for prop, raw in properties.items():
        if prop in (14, 15, 16, 25):
            continue
        if prop not in (18, 19, 20, 21):
            raise ValueError(f'Unsupported 7z file property {prop:#x}')
        values = Reader(raw)
        defined = [True] * count if values.byte() else values.bits(count)
        values.expect(0)
        for row, yes in zip(entries, defined):
            row[prop] = values.take(4 if prop == 21 else 8) if yes else None
        values.end()
    if sum(not row['empty'] for row in entries) != len(folders) or sum(packed) != offset:
        raise ValueError('7z streams do not match file metadata')
    if any(value is None for value in digests):
        raise ValueError('Missing file CRC in 7z input')
    return packed, folders, sizes, digests, entries


def make_header(packed, folders, sizes, digests, entries):
    # Put directory records first without changing the order of data streams.
    entries = sorted(entries, key=lambda row: not (row['empty'] and not row['file']))
    out = bytearray(b'\x01')
    if packed:
        out += b'\x04\x06\x00' + number(len(packed)) + b'\x09'
        out += b''.join(map(number, packed)) + b'\x00\x07\x0b' + number(len(folders)) + b'\x00'
        out += b''.join(folders) + b'\x0c'
        out += b''.join(number(value) for folder in sizes for value in folder)
        out += b'\x0a' + defined_values(digests) + b'\x00\x08\x00\x00'
    out += b'\x05' + number(len(entries))
    def prop(kind, data):
        out.extend(bytes([kind]) + number(len(data)) + data)
    empty = [row['empty'] for row in entries]
    if any(empty):
        prop(14, bits(empty))
        empty_files = [row['file'] for row in entries if row['empty']]
        if any(empty_files):
            prop(15, bits(empty_files))
    prop(17, b'\x00' + ''.join(row['name'] + '\0' for row in entries).encode('utf-16le'))
    for kind in (18, 19, 20, 21):
        values = [row.get(kind) for row in entries]
        if any(value is not None for value in values):
            prop(kind, defined_values(values, external=True))
    return bytes(out) + b'\x00\x00'


def assemble(output, inputs):
    """Write each input's packed bytes once, replacing only its metadata names."""
    output = Path(output)
    packed, folders, sizes, digests, entries = [], [], [], [], []
    sources = []
    for path, renames in inputs:
        path = Path(path)
        if path.resolve() == output.resolve():
            raise ValueError('7z output must differ from inputs')
        stream_sizes, folder_records, unpack_sizes, file_crcs, files = read_archive(path, renames)
        packed.extend(stream_sizes)
        folders.extend(folder_records)
        sizes.extend(unpack_sizes)
        digests.extend(file_crcs)
        entries.extend(files)
        sources.append((path, sum(stream_sizes), path.stat()))
    names = [row['name'] for row in entries]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate output archive paths')
    header = make_header(packed, folders, sizes, digests, entries)
    start = struct.pack('<QQI', sum(packed), len(header), zlib.crc32(header))
    signature = SIGNATURE + struct.pack('<I', zlib.crc32(start)) + start
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.name + f'.partial.{os.getpid()}')
    try:
        with partial.open('xb') as dest:
            dest.write(signature)
            for path, remaining, before in sources:
                with path.open('rb') as source:
                    source.seek(32)
                    while remaining:
                        chunk = source.read(min(8 * 1024 * 1024, remaining))
                        if not chunk:
                            raise ValueError(f'Truncated packed data: {path}')
                        dest.write(chunk)
                        remaining -= len(chunk)
                after = path.stat()
                if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                    raise ValueError(f'Input archive changed during assembly: {path}')
            dest.write(header)
        # Re-read the small header and its checksums before publication.
        read_archive(partial, {})
        partial.replace(output)
    finally:
        partial.unlink(missing_ok=True)
