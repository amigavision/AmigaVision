#!/usr/bin/env python3

# Packbit codec based on packbits.py by Mikhail Korobov (https://github.com/kmike/packbits)
# IFF ILBM encoder based on imgtoiff.py by Per Olofsson (https://github.com/MagerValp/ArcadeGameSelector)

import array
import enum
import math
import struct
import sys

# -----------------------------------------------------------------------------
# Packbits codec

def packbits_decode(data):
    data = bytearray(data)
    result = bytearray()
    pos = 0

    while pos < len(data):
        header_byte = data[pos]
        if header_byte > 127:
            header_byte -= 256
        pos += 1

        if 0 <= header_byte <= 127:
            result.extend(data[pos:pos + header_byte + 1])
            pos += header_byte + 1
        elif header_byte == -128:
            pass
        else:
            result.extend([data[pos]] * (1 - header_byte))
            pos += 1

    return bytes(result)

def packbits_encode(data):
    class State(enum.Enum):
        RAW = 0
        RLE = 1

    MAX_LENGTH = 127

    if len(data) == 0:
        return bytes(b'')
    if len(data) == 1:
        return bytes(b'\x00' + data)

    data = bytearray(data)
    result = bytearray()
    buf = bytearray()
    pos = 0
    rep = 0
    state = State.RAW

    def raw_end():
        if len(buf) == 0: return
        result.append(len(buf) - 1)
        result.extend(buf)
        buf[:] = bytearray()

    def rle_end():
        result.append(256 - (rep - 1))
        result.append(data[pos])

    while pos < len(data)-1:
        current_byte = data[pos]
        if data[pos] == data[pos + 1]:
            if state == State.RAW:
                raw_end()
                state = State.RLE
                rep = 1
            elif state == State.RLE:
                if rep == MAX_LENGTH:
                    rle_end()
                    rep = 0
                rep += 1
        else:
            if state == State.RLE:
                rep += 1
                rle_end()
                state = State.RAW
                rep = 0
            elif state == State.RAW:
                if len(buf) == MAX_LENGTH:
                    raw_end()
                buf.append(current_byte)
        pos += 1

    if state == State.RAW:
        buf.append(data[pos])
        raw_end()
    else:
        rep += 1
        rle_end()
    return bytes(result)

# -----------------------------------------------------------------------------
# IFF ILMB encoder

def next_pow2(n):
    return int(math.pow(2, math.ceil(math.log(n) / math.log(2))))

def chunk(id, *data):
    id = bytes("{0:<4}".format(id[0:4]).encode("ascii"))
    blob = bytes()
    for d in data: blob += d
    length = len(blob)
    if len(blob) & 1: blob += b'0'
    return bytes(id + struct.pack(">L", length) + blob)

def header(width, height, palette, mode, pack):
    depth = int(math.ceil(math.log(len(palette), 2)))
    bmhd = chunk("BMHD", struct.pack(">HHHHBBBxHBBHH",
        width,  # w:INT
        height, # h:INT
        0,      # x:INT
        0,      # y:INT
        depth,  # nplanes:CHAR
        0,      # masking:CHAR
        pack,   # compression:CHAR
                # pad:CHAR
        0,      # transparentcolor:INT
        60,     # xaspect:CHAR
        60,     # yaspect:CHAR
        width,  # pagewidth:INT
        height, # pageheight:INT
    ))

    p = bytes()
    for (r, g, b) in palette:
        p += struct.pack("BBB", r, g, b)
    cmap = chunk("CMAP", p)

    if mode is not None:
        camg = chunk("CAMG", bytes(struct.pack(">L", mode)))
    else:
        camg = b''
    return depth, bmhd, cmap, camg

def planar_data(width, height, depth, pixels):
    plane_width = ((width + 15) // 16) * 16
    bpr = plane_width // 8
    plane_size = bpr * height

    planes = tuple(array.array("B", (0 for i in range(plane_size))) for j in range(depth))
    for y in range(height):
        rowoffset = y * bpr
        for x in range(width):
            offset = rowoffset + x // 8
            xmod = 7 - (x & 7)
            p = pixels[x, y]
            for plane in range(depth):
                planes[plane][offset] |= ((p >> plane) & 1) << xmod
    return bpr, planes

def palette_data(palette):
    p = []
    for i in range(len(palette) // 3):
        p.append((palette[i * 3], palette[i * 3 + 1], palette[i * 3 + 2]))
    p.extend([(0,0,0)] * (next_pow2(len(p)) - len(p)))
    return p

def ilbm(width, height, pixels, palette, mode=0x29000, pack=1):
    depth, bmhd, cmap, camg = header(width, height, palette_data(palette), mode, pack)
    bpr, planes = planar_data(width, height, depth, pixels)

    rows = []
    for y in range(height):
        for row in (planes[plane][y * bpr:y * bpr + bpr].tostring() for plane in range(depth)):
            rows.append(row)

    body_data = bytes()
    for r in rows:
        if pack == 0:
            body_data += r
        else:
            body_data += packbits_encode(r)

    return chunk("FORM", "ILBM".encode("ascii"), bmhd, cmap, camg, chunk("BODY", body_data))

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("not runnable")
    sys.exit(1)
