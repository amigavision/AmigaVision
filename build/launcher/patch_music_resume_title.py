#!/usr/bin/env python3
"""Redisplay Now Playing when the native music task resumes playback."""
from pathlib import Path
import argparse
import struct

TAG = b'AVSRESM1'
HOOK = 0x8506
ORIGINAL = bytes.fromhex('204621400036')


def remove_patch(data):
    from patch_favorite_screenshots import remove_patch as remove_favorites
    data = remove_favorites(data)
    from patch_popup_up import remove_patch as remove_popup
    data = remove_popup(data)
    end = 32 + struct.unpack_from('>I', data, 28)[0]*4
    if data[end-12:end-4] != TAG:
        return data
    size = struct.unpack_from('>I', data, end-4)[0]
    result = bytearray(data[:32+size]+data[end:])
    for offset in (20, 28):
        struct.pack_into('>I', result, offset, size//4)
    result[32+HOOK:32+HOOK+6] = ORIGINAL
    return bytes(result)


def patch(data):
    size = struct.unpack_from('>I', data, 28)[0] * 4
    end = 32 + size
    if data[end-12:end-4] == TAG:
        return data
    if data[32+HOOK:32+HOOK+6] != ORIGINAL:
        raise ValueError('Unknown native music resume hook')
    # Follow appended layer footers to the existing notification state table.
    layer_end = end
    while data[layer_end-12:layer_end-4] != b'AVSNOW04':
        if data[layer_end-12:layer_end-4] not in (b'AVSCANC1', b'AVSEXIT1', b'AVSVIEW3'):
            raise ValueError('Unknown menu patch chain')
        layer_end = 32 + struct.unpack_from('>I', data, layer_end-4)[0]
    base = struct.unpack_from('>I', data, layer_end-4)[0]
    state = base + struct.unpack_from('>I', data, 32+base+16)[0]
    blob = bytearray.fromhex('48e78080 4a80 6706 41fa0000 5290 4cdf0101')
    # d0 is the native new playing state: zero paused, nonzero resumed.
    struct.pack_into('>h', blob, 10, state-(size+10))
    blob += ORIGINAL
    blob += struct.pack('>Hh', 0x6000, HOOK+6-(size+len(blob)+2))
    blob += bytes((-len(blob)) % 4)
    blob += TAG + struct.pack('>I', size)
    result = bytearray(data[:end]+blob+data[end:])
    for offset in (20, 28):
        struct.pack_into('>I', result, offset, (size+len(blob))//4)
    result[32+HOOK:32+HOOK+6] = struct.pack('>HhH', 0x6000, size-(HOOK+2), 0x4e71)
    return bytes(result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('menu', type=Path)
    args = parser.parse_args()
    args.menu.write_bytes(patch(args.menu.read_bytes()))
