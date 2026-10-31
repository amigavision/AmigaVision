#!/usr/bin/env python3
"""Experimental single-stream XZ block reuse; never used by make distros.

Format: https://tukaani.org/xz/xz-file-format.txt
Only one CRC64 source stream, no stream padding, source blocks <=64 MiB.
Every reused block is decoded and compared with its target bytes first.
The entire output is independently decoded and SHA-256 checked before publish.
"""
import argparse
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
import json
import lzma
import os
from pathlib import Path
import struct
import subprocess
from time import monotonic
import zlib

FLAGS = b'\x00\x04'  # CRC64
HEADER = b'\xfd7zXZ\x00' + FLAGS + struct.pack('<I', zlib.crc32(FLAGS))
MAX_BLOCK = 64 * 1024**2


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


def encoded_block(data):
    stream = lzma.compress(data, preset=1, check=lzma.CHECK_CRC64)
    # lzma.compress produces one block; its index is tiny.
    length = (struct.unpack_from('<I', stream, len(stream) - 8)[0] + 1) * 4
    metadata = stream[-12-length:-12]
    count, pos = read_vli(metadata, 1)
    unpadded, pos = read_vli(metadata, pos)
    raw_size, pos = read_vli(metadata, pos)
    if count != 1 or raw_size != len(data):
        raise ValueError('Compressor did not produce one expected XZ block')
    return stream[12:-12-length], (unpadded, raw_size)


def read_exact(file, count):
    data = file.read(count)
    if len(data) != count:
        raise ValueError('Truncated input')
    return data


def stamp(path):
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def reuse(seed, target, output, prefix=None, padding=0, workers=4, xz='xz'):
    seed, target, output = map(Path, (seed, target, output))
    prefix = Path(prefix) if prefix else None
    paths = [seed, target] + ([prefix] if prefix else [])
    if output.resolve() in [path.resolve() for path in paths]:
        raise ValueError('Output must differ from every input')
    if not 1 <= workers <= 8 or not 0 <= padding <= 1024**2:
        raise ValueError('Unsupported worker count or partition padding')
    snapshots = [(path, stamp(path)) for path in paths]
    blocks = index(seed)
    if sum(block.raw_size for block in blocks) != target.stat().st_size:
        raise ValueError('Seed and target uncompressed sizes differ')
    if prefix and prefix.stat().st_size > 128 * 1024**2:
        raise ValueError('Prefix exceeds prototype limit')
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.name + f'.partial.{os.getpid()}')
    digest, records = hashlib.sha256(), []
    result = dict(blocks=len(blocks), reused_blocks=0, changed_blocks=0,
                  reused_raw_bytes=0, changed_raw_bytes=0)
    started, last_report = monotonic(), monotonic()

    def process(block):
        with seed.open('rb') as source:
            source.seek(block.offset)
            packed = read_exact(source, block.packed_size)
        raw = lzma.decompress(HEADER + packed + trailer([(block.unpadded, block.raw_size)]))
        if len(raw) != block.raw_size:
            raise ValueError('Seed XZ block differs from index size')
        with target.open('rb') as source:
            source.seek(block.raw_offset)
            wanted = read_exact(source, block.raw_size)
        unchanged = raw == wanted
        if unchanged:
            return packed, (block.unpadded, block.raw_size), wanted, True
        packed, record = encoded_block(wanted)
        return packed, record, wanted, False

    try:
        with partial.open('xb') as dest, ThreadPoolExecutor(max_workers=workers) as pool:
            dest.write(HEADER)
            if prefix and prefix.stat().st_size:
                data = prefix.read_bytes()
                packed, record = encoded_block(data)
                dest.write(packed); records.append(record); digest.update(data)
            pending, iterator = deque(), iter(blocks)
            # Bounded queue: at most two blocks per worker, never the whole HDF.
            for _ in range(workers * 2):
                block = next(iterator, None)
                if block: pending.append(pool.submit(process, block))
            while pending:
                packed, record, raw, unchanged = pending.popleft().result()
                dest.write(packed); records.append(record); digest.update(raw)
                key = 'reused' if unchanged else 'changed'
                result[key + '_blocks'] += 1
                result[key + '_raw_bytes'] += len(raw)
                block = next(iterator, None)
                if block: pending.append(pool.submit(process, block))
                if monotonic() - last_report >= 15:
                    done = result['reused_blocks'] + result['changed_blocks']
                    print(f'XZ reuse: {done}/{len(blocks)} HDF blocks; '
                          f'{result["changed_blocks"]} changed; {monotonic()-started:.0f}s', flush=True)
                    last_report = monotonic()
            if padding:
                raw = bytes(padding)
                packed, record = encoded_block(raw)
                dest.write(packed); records.append(record); digest.update(raw)
            dest.write(trailer(records))
        result['assembly_seconds'] = round(monotonic() - started, 2)
        verification = monotonic()
        last_report = verification
        print('XZ reuse: independently verifying complete output...', flush=True)
        actual, size = hashlib.sha256(), 0
        with subprocess.Popen([xz, '-T0', '-dc', str(partial)], stdout=subprocess.PIPE) as process:
            try:
                while chunk := process.stdout.read(4 * 1024**2):
                    actual.update(chunk); size += len(chunk)
                    if monotonic() - last_report >= 15:
                        print(f'XZ reuse verification: {size / 1024**3:.2f} GiB; '
                              f'{monotonic()-verification:.0f}s', flush=True)
                        last_report = monotonic()
                if process.wait():
                    raise subprocess.CalledProcessError(process.returncode, process.args)
            finally:
                if process.poll() is None:
                    process.kill(); process.wait()
        expected_size = target.stat().st_size + (prefix.stat().st_size if prefix else 0) + padding
        if actual.digest() != digest.digest() or size != expected_size:
            raise ValueError('Independent XZ decompression differs from requested image')
        for path, before in snapshots:
            if stamp(path) != before:
                raise ValueError(f'Input changed during experiment: {path}')
        result.update(verification_seconds=round(monotonic()-verification, 2),
                      total_seconds=round(monotonic()-started, 2), output_bytes=partial.stat().st_size,
                      sha256_uncompressed=digest.hexdigest())
        partial.replace(output)
        return result
    finally:
        partial.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=Path, required=True)
    parser.add_argument('--target', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prefix', type=Path)
    parser.add_argument('--padding', type=int, default=0)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = reuse(args.seed, args.target, args.output, args.prefix, args.padding, args.workers)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
