#!/usr/bin/env python3
"""Defer QUIT acknowledgement until the validated hi-res helper finishes cleanup.

Apply LAST, after QR composition. Only this exact helper baseline is supported.
The software interrupt retains the message and returns; it never waits. The
normal task replies at its common exit after timer, image, port and stage cleanup.
All added references are PC-relative, so the existing HUNK relocation tail stays
unchanged. No Chip RAM allocation or image-loading behavior is added.
"""
import argparse
import hashlib
import struct
from pathlib import Path

BASELINE = 'd9b1303df11fc1f78b758be7debde96fc7c87fc3171a28324c2a2c1e6ccf6917'
TAG = b'AVSQUIT1'
HOOKS = ((0x3870, bytes.fromhex('206d0008')),
         (0x4868, bytes.fromhex('7000dffc00000344')))


def remove_patch(data):
    size = struct.unpack_from('>I', data, 28)[0] * 4
    end = 32 + size
    if data[end-12:end-4] == TAG:
        original_size = struct.unpack_from('>I', data, end-4)[0]
        restored = bytearray(data[:32+original_size] + data[end:])
        for off in (20, 28):
            struct.pack_into('>I', restored, off, original_size//4)
        for addr, original in HOOKS:
            restored[32+addr:32+addr+len(original)] = original
        if hashlib.sha256(restored).hexdigest() != BASELINE:
            raise ValueError('Unrecognized modified shutdown patch')
        return bytes(restored)
    return data


def patch(data):
    original = remove_patch(data)
    if original != data:
        return data
    size = struct.unpack_from('>I', data, 28)[0] * 4
    end = 32 + size
    if hashlib.sha256(data).hexdigest() != BASELINE:
        raise ValueError('Unknown helper; revalidate shutdown offsets before patching')
    for addr, expected in HOOKS:
        assert data[32+addr:32+addr+len(expected)] == expected

    blob = bytearray(8)  # entry offsets, relative to appended block
    labels, fixups = {}, []
    def mark(name): labels[name] = size + len(blob)
    def emit(hexcode): blob.extend(bytes.fromhex(hexcode))
    def relative(opcode, target):
        emit(opcode)
        fixups.append((len(blob), target))
        blob.extend(bytes(2))

    mark('defer')
    relative('43fa', 'pending')       # lea pending(pc),a1
    emit('2287')                    # move.l d7,(a1), retain QUIT message
    relative('6000', 0x3a38)         # return handler WITHOUT ReplyMsg

    mark('finish')
    emit('48e7fffe')                 # movem.l d0-d7/a0-a6,-(sp)
    relative('41fa', 'pending')
    emit('4a90')                    # tst.l (a0)
    relative('6700', 'restore')
    emit('2c6cffcc4eaeff1c')         # graphicsbase; WaitBlit
    relative('41fa', 'pending')
    emit('22504290')                # movea.l (a0),a1; clr.l (a0)
    emit('2c6cffd84eaefe86')         # execbase; ReplyMsg(a1)
    mark('restore')
    emit('4cdf7fff')                 # movem.l (sp)+,d0-d7/a0-a6
    emit('7000dffc00000344')         # replay original exit stack adjustment
    relative('6000', 0x4870)
    mark('pending')
    emit('00000000')
    while len(blob) % 4:
        emit('0000')
    blob.extend(TAG + struct.pack('>I', size))
    struct.pack_into('>II', blob, 0, labels['defer']-size, labels['finish']-size)
    for pos, target in fixups:
        target = labels[target] if isinstance(target,str) else target
        struct.pack_into('>h', blob, pos, target-(size+pos))
    result = bytearray(data[:end] + blob + data[end:])
    for off in (20,28):
        struct.pack_into('>I', result, off, (size+len(blob))//4)
    for (addr, original), target in zip(HOOKS, ('defer','finish')):
        result[32+addr:32+addr+len(original)] = (
            struct.pack('>Hh', 0x6000, labels[target]-(addr+2))
            + bytes.fromhex('4e71')*((len(original)-4)//2))
    assert result[32+size+len(blob):] == data[end:]
    return bytes(result)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('helper',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.write_bytes(patch(args.helper.read_bytes()))
