#!/usr/bin/env python3
"""Route the literal Exit to Workbench item through the native ESC quit action.

Apply after the viewport patch. Existing F-prefixed menu caches remain valid.
The hook runs before file activation, without creating a run script or loader.
"""
import argparse
import hashlib
from pathlib import Path
import struct

BASELINE = 'a0a03c0c5de5e7123300a2a38e1d7577e2313082a4b58a9a4f5b291e8e251c18'
TAG = b'AVSEXIT1'
HOOK = 0x4fba
ORIGINAL = bytes.fromhex('20060c8000000006')


def remove_patch(data):
    end = 32 + struct.unpack_from('>I', data, 28)[0] * 4
    if data[end-12:end-4] != TAG:
        return data
    size = struct.unpack_from('>I', data, end-4)[0]
    restored = bytearray(data[:32+size] + data[end:])
    for offset in (20, 28):
        struct.pack_into('>I', restored, offset, size // 4)
    restored[32+HOOK:32+HOOK+len(ORIGINAL)] = ORIGINAL
    if hashlib.sha256(restored).hexdigest() != BASELINE:
        raise ValueError('Unrecognized exit-patched menu')
    return bytes(restored)


def patch(data):
    if remove_patch(data) != data:
        return data
    if hashlib.sha256(data).hexdigest() != BASELINE:
        raise ValueError('Unknown menu; revalidate exit hook before patching')
    assert data[32+HOOK:32+HOOK+len(ORIGINAL)] == ORIGINAL
    size = struct.unpack_from('>I', data, 28)[0] * 4
    end = 32 + size
    blob = bytearray()
    labels, fixups = {}, []

    def emit(hexcode):
        blob.extend(bytes.fromhex(hexcode))

    def mark(name):
        labels[name] = size + len(blob)

    def relative(opcode, target):
        emit(opcode)
        fixups.append((len(blob), target))
        blob.extend(bytes(2))

    emit('48e7e0e0')                 # save d0-d2/a0-a2
    emit('0c8600000006')             # primary activation action?
    relative('6600', 'done')
    emit('204470003028002472003228002ad081')  # selected row + scroll offset
    emit('206800084a80')             # navigator; reject invalid index
    relative('6b00', 'done')
    emit('b0a80010')                 # compare against item count
    relative('6c00', 'done')
    emit('20680014e58820700800')      # selected item pointer
    emit('0ca8000000020008')          # native file item, not directory
    relative('6600', 'done')
    emit('2050')                     # owned item name
    relative('43fa', 'name')
    mark('compare')
    emit('1018b019')                 # compare bytes, including terminating NUL
    relative('6600', 'done')
    emit('4a00')
    relative('6600', 'compare')
    emit('7c05')                     # same quit action returned by root ESC
    mark('done')
    emit('4cdf0707')                 # restore d0-d2/a0-a2
    blob.extend(ORIGINAL)            # native dispatch comparison, with new d6
    relative('6000', HOOK + len(ORIGINAL))
    mark('name')
    blob.extend(b'Exit to Workbench\0')
    for offset, target in fixups:
        target = labels[target] if isinstance(target, str) else target
        struct.pack_into('>h', blob, offset, target - (size + offset))
    blob.extend(bytes((-len(blob)) % 4))
    blob.extend(TAG + struct.pack('>I', size))
    result = bytearray(data[:end] + blob + data[end:])
    for offset in (20, 28):
        struct.pack_into('>I', result, offset, (size + len(blob)) // 4)
    result[32+HOOK:32+HOOK+len(ORIGINAL)] = (
        struct.pack('>Hh', 0x6000, size - (HOOK + 2)) + bytes.fromhex('4e714e71'))
    return bytes(result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('menu', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_bytes(patch(args.menu.read_bytes()))
