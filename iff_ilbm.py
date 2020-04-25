#!/usr/bin/env python3

# IFF ILBM encoder based on imgtoiff.py by Per Olofsson (https://github.com/MagerValp/ArcadeGameSelector)

import array
import enum
import math
import struct
import sys
from itertools import groupby

# -----------------------------------------------------------------------------

def next_pow2(n):
    return int(math.pow(2, math.ceil(math.log(n) / math.log(2))))

def packbits(data):
    max_size = 127
    out = bytes()
    lit = bytes()

    def block_sizes(length, max):
        return [max] * divmod(length,max)[0] + [divmod(length,max)[1]]

    def lit_end():
        nonlocal out, lit
        for i, s in enumerate(block_sizes(len(lit), max_size)):
            if not s: continue
            out += struct.pack("b", s - 1)
            out += lit[i * max_size:i * max_size + max_size]
        lit = bytes()

    for length, value in [(len(list(g)), struct.pack("B", k)) for k, g in groupby(bytearray(data))]:
        if length == 1:
            lit += value
        else:
            lit_end()
            for s in  block_sizes(length, max_size):
                out += struct.pack("b", 1 - s)
                out += value
    lit_end()
    return out

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
            body_data += packbits(r)

    return chunk("FORM", "ILBM".encode("ascii"), bmhd, cmap, camg, chunk("BODY", body_data))

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("not runnable")
    sys.exit(1)
