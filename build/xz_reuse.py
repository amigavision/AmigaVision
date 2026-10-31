#!/usr/bin/env python3
"""Build single-stream XZ images by reusing SHA-256-matched seed blocks.

The seed manifest is produced while streaming the original HDF into xz.
Reused blocks are never decoded here. Full-output independent decompression
and SHA-256 verification are mandatory before atomic publication.
Format reference: https://tukaani.org/xz/xz-file-format.txt
"""
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import lzma
import os
from pathlib import Path
import struct
import subprocess
from time import monotonic
import zlib
import threading
from contextlib import contextmanager

FLAGS = b'\x00\x04'  # CRC64
HEADER = b'\xfd7zXZ\x00' + FLAGS + struct.pack('<I', zlib.crc32(FLAGS))
MAX_BLOCK = 64 * 1024**2
BLOCK_SIZE = 3 * 1024**2


class ReuseUnavailable(ValueError):
    """No compatible seed exists; ordinary compression is appropriate."""


@dataclass(frozen=True)
class Segment:
    path: Path | None
    offset: int
    length: int
    reusable: bool = False


def stamp(path):
    stat = Path(path).stat()
    return [stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns]


def describe_stamp(value):
    modified = datetime.fromtimestamp(value[1] / 1e9).astimezone().isoformat(timespec='microseconds')
    return f'{value[0]} bytes, modified {modified}, mtime_ns={value[1]}, ctime_ns={value[2]}'


def compression_environment(output):
    directory = str(Path(output).parent.resolve())
    return dict(os.environ, TMPDIR=directory, TMP=directory, TEMP=directory)


@contextmanager
def progress(label, total, output=None):
    state = [0]
    stop = threading.Event()
    started = monotonic()

    def report():
        detail = f'{state[0] / 1024**3:.2f}/{total / 1024**3:.2f} GiB'
        if output is not None:
            detail += f'; output {output.stat().st_size / 1024**3:.2f} GiB'
        print(f'{label}: {detail}; elapsed {monotonic()-started:.0f}s', flush=True)

    def monitor():
        while not stop.wait(15):
            report()

    report()
    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    try:
        yield state
    finally:
        stop.set(); thread.join()
    report()


def crc(data):
    return struct.pack('<I', zlib.crc32(data))


def vli(value):
    if not 0 <= value < 1 << 63:
        raise ValueError('XZ integer outside supported range')
    data = bytearray()
    while value >= 128:
        data.append((value & 127) | 128)
        value >>= 7
    data.append(value)
    return bytes(data)


def read_vli(data, pos):
    value = 0
    for shift in range(0, 63, 7):
        if pos >= len(data):
            raise ValueError('Truncated XZ integer')
        byte = data[pos]; pos += 1
        if shift and byte == 0:
            raise ValueError('Noncanonical XZ integer')
        value |= (byte & 127) << shift
        if not byte & 128:
            return value, pos
    raise ValueError('Oversized XZ integer')


def trailer(records):
    index = b'\x00' + vli(len(records)) + b''.join(vli(a) + vli(b) for a, b in records)
    index += bytes((-len(index)) % 4)
    index += crc(index)
    footer = struct.pack('<I', len(index) // 4 - 1) + FLAGS
    return index + crc(footer) + footer + b'YZ'


@dataclass(frozen=True)
class Block:
    offset: int
    raw_offset: int
    unpadded: int
    raw_size: int

    @property
    def packed_size(self):
        return (self.unpadded + 3) & ~3


def index(path):
    """Read and validate the small stream metadata, not the full payload."""
    with Path(path).open('rb') as file:
        if file.read(12) != HEADER:
            raise ValueError('Expected a CRC64 XZ stream')
        file.seek(0, 2); size = file.tell()
        if size < 32 or size % 4:
            raise ValueError('Invalid XZ file size')
        file.seek(-12, 2); footer = file.read(12)
        if footer[-2:] != b'YZ' or footer[8:10] != FLAGS or crc(footer[4:10]) != footer[:4]:
            raise ValueError('Invalid XZ footer')
        length = (struct.unpack_from('<I', footer, 4)[0] + 1) * 4
        if length > 64 * 1024**2 or length > size - 24:
            raise ValueError('Invalid XZ index size')
        start = size - 12 - length
        file.seek(start); data = file.read(length)
    if data[0] != 0 or crc(data[:-4]) != data[-4:]:
        raise ValueError('Invalid XZ index CRC/indicator')
    count, pos = read_vli(data[:-4], 1)
    if count > 1000000:
        raise ValueError('Too many XZ blocks')
    blocks, offset, raw_offset = [], 12, 0
    for _ in range(count):
        unpadded, pos = read_vli(data[:-4], pos)
        raw_size, pos = read_vli(data[:-4], pos)
        if not 9 <= unpadded <= 2 * MAX_BLOCK or not 0 < raw_size <= MAX_BLOCK:
            raise ValueError('Unsupported XZ block size')
        block = Block(offset, raw_offset, unpadded, raw_size)
        blocks.append(block)
        offset += block.packed_size; raw_offset += raw_size
    if offset != start or len(data) - 4 - pos > 3 or any(data[pos:-4]):
        raise ValueError('Invalid XZ block bounds/index padding (one stream required)')
    return blocks


def read_exact(file, count):
    data = file.read(count)
    if len(data) != count:
        raise ValueError('Truncated image input')
    return data


def encoded_block(data):
    """Compress one block and supply sizes for multithreaded xz decoding."""
    stream = lzma.compress(data, preset=1, check=lzma.CHECK_CRC64)
    index_size = (struct.unpack_from('<I', stream, len(stream) - 8)[0] + 1) * 4
    metadata = stream[-12-index_size:-12]
    count, pos = read_vli(metadata, 1)
    unpadded, pos = read_vli(metadata, pos)
    raw_size, pos = read_vli(metadata, pos)
    if count != 1 or raw_size != len(data):
        raise ValueError('Expected one compressed XZ block')
    block = stream[12:-12-index_size]
    old_size = (block[0] + 1) * 4
    if crc(block[:old_size-4]) != block[old_size-4:old_size]:
        raise ValueError('Invalid compressor block header')
    flags, pos = block[1], 2
    if flags & 0x3c:
        raise ValueError('Unsupported compressor flags')
    if flags & 0x40: _, pos = read_vli(block, pos)
    if flags & 0x80: _, pos = read_vli(block, pos)
    filters_start = pos
    for _ in range((flags & 3) + 1):
        _, pos = read_vli(block, pos)
        size, pos = read_vli(block, pos)
        pos += size
    if pos > old_size - 4:
        raise ValueError('Invalid compressor filter metadata')
    compressed_size = unpadded - old_size - 8
    header = bytearray(b'\x00' + bytes([flags | 0xc0]) + vli(compressed_size) + vli(raw_size) + block[filters_start:pos])
    header += bytes((-len(header) - 4) % 4)
    header[0] = (len(header) + 4) // 4 - 1
    header += crc(header)
    return bytes(header) + block[old_size:], (unpadded + len(header) - old_size, raw_size)


def compress_seed(source, output, manifest, xz='xz'):
    """Capture hashes of the exact input bytes supplied to preset-1 xz."""
    source, output, manifest = map(Path, (source, output, manifest))
    if len({path.resolve() for path in (source, output, manifest)}) != 3:
        raise ValueError('Seed source, archive, and manifest must differ')
    before = stamp(source)
    print(f'XZ seed source: {source}: {describe_stamp(before)}', flush=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.name + f'.partial.{os.getpid()}')
    metadata_partial = manifest.with_name(manifest.name + f'.partial.{os.getpid()}')
    hashes = []
    try:
        with partial.open('xb') as dest, progress('XZ compression + block hashes', before[0], partial) as state:
            with subprocess.Popen([xz, '--format=xz', '--check=crc64', '-T0', '-1', f'--block-size={BLOCK_SIZE}', '-c'],
                                  stdin=subprocess.PIPE, stdout=dest, env=compression_environment(output)) as process:
                try:
                    with source.open('rb') as file:
                        while data := file.read(BLOCK_SIZE):
                            hashes.append(hashlib.sha256(data).hexdigest())
                            process.stdin.write(data)
                            state[0] += len(data)
                    process.stdin.close()
                    if process.wait():
                        raise subprocess.CalledProcessError(process.returncode, process.args)
                except BaseException:
                    process.kill(); process.wait(); raise
        blocks = index(partial)
        after = stamp(source)
        if after != before:
            raise ValueError(f'Source changed during compression: {source}; '
                             f'before: {describe_stamp(before)}; after: {describe_stamp(after)}')
        compressed_raw_bytes = sum(b.raw_size for b in blocks)
        if len(blocks) != len(hashes) or compressed_raw_bytes != before[0]:
            raise ValueError('Compressor block layout differs: '
                             f'{len(blocks)} blocks vs {len(hashes)} captured hashes; '
                             f'{compressed_raw_bytes} decoded bytes vs {before[0]} source bytes')
        if any(b.raw_size != min(BLOCK_SIZE, before[0]-b.raw_offset) for b in blocks):
            raise ValueError('Unexpected compressor block boundaries')
        partial.replace(output)
        metadata = dict(schema=1, block_size=BLOCK_SIZE, raw_bytes=before[0],
                        seed_stamp=stamp(output), hashes=hashes)
        metadata_partial.write_text(json.dumps(metadata) + '\n')
        metadata_partial.replace(manifest)
    finally:
        partial.unlink(missing_ok=True)
        metadata_partial.unlink(missing_ok=True)


def load_seed(seed, manifest):
    """Reject missing/stale manifests before beginning any output work."""
    try:
        if manifest.stat().st_size > 8 * 1024**2:
            raise ValueError('Manifest exceeds size limit')
        metadata = json.loads(manifest.read_text())
        blocks = index(seed)
        hashes = metadata['hashes']
        if (metadata['schema'] != 1 or metadata['block_size'] != BLOCK_SIZE or
                metadata['seed_stamp'] != stamp(seed) or len(hashes) != len(blocks) or
                metadata['raw_bytes'] != sum(b.raw_size for b in blocks)):
            raise ValueError('Seed manifest is stale or incompatible')
        for i, (block, digest) in enumerate(zip(blocks, hashes)):
            if (block.raw_offset != i * BLOCK_SIZE or
                    block.raw_size != min(BLOCK_SIZE, metadata['raw_bytes']-block.raw_offset) or
                    len(bytes.fromhex(digest)) != 32):
                raise ValueError('Invalid block hashes/boundaries')
        return blocks, [value.lower() for value in hashes]
    except (FileNotFoundError, ValueError, KeyError, TypeError, AttributeError) as error:
        raise ReuseUnavailable(str(error)) from error


def reuse(seed, manifest, output, segments, label='XZ reuse', xz='xz', workers=4):
    seed, manifest, output = map(Path, (seed, manifest, output))
    inputs = {Path(s.path) for s in segments if s.path is not None} | {seed, manifest}
    if output.resolve() in {path.resolve() for path in inputs}:
        raise ValueError('Output must differ from inputs')
    snapshots = []
    for path in inputs:
        try:
            snapshots.append((path, stamp(path)))
        except FileNotFoundError as error:
            if path in (seed, manifest):
                raise ReuseUnavailable(f'Missing seed/manifest: {path}') from error
            raise
    blocks, hashes = load_seed(seed, manifest)
    raw_size = sum(block.raw_size for block in blocks)
    if not 1 <= workers <= 8 or not segments or not any(s.reusable for s in segments):
        raise ValueError('Expected a reusable segment and 1–8 workers')
    for segment in segments:
        if segment.offset < 0 or segment.length < 0:
            raise ValueError('Negative image range')
        if segment.path is not None and segment.offset + segment.length > Path(segment.path).stat().st_size:
            raise ValueError('Image range exceeds source')
        if segment.reusable and (segment.path is None or segment.length != raw_size):
            raise ReuseUnavailable('Seed and embedded HDF sizes differ')
    total = sum(s.length for s in segments)

    def tasks():
        for segment in segments:
            if segment.reusable:
                for block, digest in zip(blocks, hashes):
                    yield segment.path, segment.offset + block.raw_offset, block.raw_size, block, digest
            else:
                for offset in range(0, segment.length, BLOCK_SIZE):
                    yield segment.path, segment.offset + offset, min(BLOCK_SIZE, segment.length-offset), None, None

    def process(task):
        path, offset, size, block, digest = task
        if path is None:
            raw = bytes(size)
        else:
            with Path(path).open('rb') as file:
                file.seek(offset); raw = read_exact(file, size)
        unchanged = block is not None and hashlib.sha256(raw).hexdigest() == digest
        if unchanged:
            with seed.open('rb') as file:
                file.seek(block.offset); packed = read_exact(file, block.packed_size)
            record = block.unpadded, block.raw_size
        else:
            packed, record = encoded_block(raw)
        return packed, record, raw, block is not None, unchanged

    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.name + f'.partial.{os.getpid()}')
    records, digest = [], hashlib.sha256()
    result = dict(reused_blocks=0, changed_blocks=0, reused_raw_bytes=0,
                  changed_raw_bytes=0, other_raw_bytes=0, seed_decoded_bytes=0)
    started = monotonic()
    try:
        with partial.open('xb') as dest, progress(label, total, partial) as state, ThreadPoolExecutor(max_workers=workers) as pool:
            dest.write(HEADER)
            iterator, pending = iter(tasks()), deque()
            for _ in range(workers * 2):
                task = next(iterator, None)
                if task is not None: pending.append(pool.submit(process, task))
            while pending:
                packed, record, raw, reusable, unchanged = pending.popleft().result()
                dest.write(packed); records.append(record); digest.update(raw)
                state[0] += len(raw)
                if reusable:
                    key = 'reused' if unchanged else 'changed'
                    result[key + '_blocks'] += 1
                    result[key + '_raw_bytes'] += len(raw)
                else:
                    result['other_raw_bytes'] += len(raw)
                task = next(iterator, None)
                if task is not None: pending.append(pool.submit(process, task))
            dest.write(trailer(records))
        result['assembly_seconds'] = round(monotonic()-started, 2)
        print(f'Timing: {label}: assembly: {result["assembly_seconds"]}s; '
              f'{result["reused_blocks"]} reused, {result["changed_blocks"]} changed HDF blocks; seed decoded: 0 bytes', flush=True)
        verification = monotonic()
        actual, size = hashlib.sha256(), 0
        with progress(label + ' verification', total) as state, \
                subprocess.Popen([xz, '-T0', '-dc', str(partial)], stdout=subprocess.PIPE,
                                 env=compression_environment(output)) as process:
            try:
                while chunk := process.stdout.read(4 * 1024**2):
                    actual.update(chunk); size += len(chunk); state[0] = size
                if process.wait():
                    raise subprocess.CalledProcessError(process.returncode, process.args)
            finally:
                if process.poll() is None:
                    process.kill(); process.wait()
        if size != total or actual.digest() != digest.digest():
            raise ValueError('Reused XZ image differs from intended image bytes')
        for path, before in snapshots:
            if stamp(path) != before:
                raise ValueError(f'Input changed during XZ reuse: {path}')
        result.update(verification_seconds=round(monotonic()-verification, 2),
                      total_seconds=round(monotonic()-started, 2), output_bytes=partial.stat().st_size,
                      sha256_uncompressed=digest.hexdigest())
        print(f'Timing: {label}: verification: {result["verification_seconds"]}s; total: {result["total_seconds"]}s', flush=True)
        partial.replace(output)
        return result
    finally:
        partial.unlink(missing_ok=True)


