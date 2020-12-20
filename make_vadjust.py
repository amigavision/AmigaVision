#!/usr/bin/env python3

# AGSImager: vadjust.dat creation utility

import sys
import os
import argparse
import struct

# -----------------------------------------------------------------------------
VADJUST_LEN = 1024

# Base settings
ntsc_h = (132, 56)
pal_h  = (132, 56)

ntsc_v = (17, 9)
pal_v5 = (17, 54)
pal_v  = (13, 4)

# mode, name, ntsc, laced
modes = [
    (0x000F25E4, "NTSC LowRes", True, False),
    (0x010F25E4, "NTSC HiRes", True, False),
    (0x020F25E4, "NTSC SuperHiRes", True, False),
    (0x001E35E4, "NTSC LowRes Laced", True, True),
    (0x011E35E4, "NTSC HiRes Laced", True, True),
    (0x021E35E4, "NTSC SuperHiRes Laced", True, True),
    (0x0011F5E4, "PAL LowRes", False, False),
    (0x0111F5E4, "PAL HiRes", False, False),
    (0x0211F5E4, "PAL SuperHiRes", False, False),
    (0x0023D5E4, "PAL LowRes Laced", False, True),
    (0x0123D5E4, "PAL HiRes Laced", False, True),
    (0x0223D5E4, "PAL SuperHiRes Laced", False, True)
]

def make_vadjust(pal_5x, v_offset):
    out = bytes()
    if v_offset is None:
        v_offset = 0

    for mode in modes:
        id = mode[0]
        ntsc = bool(mode[2])
        lace = bool(mode[3])

        # get base values
        if ntsc:
            h1 = ntsc_h[0]
            h2 = ntsc_h[1]
            v1 = ntsc_v[0]
            v2 = ntsc_v[1]
        else:
            h1 = pal_h[0]
            h2 = pal_h[1]
            if pal_5x:
                v1 = pal_v5[0]
                v2 = pal_v5[1]
            else:
                v1 = pal_v[0]
                v2 = pal_v[1]
        # interlace adjustment
        if lace:
            v2 -= 1
        # second value negative
        h2 = 4096 - h2
        v2 = 4096 - v2
        # adjust for offset
        if v_offset != 0:
            vofs = v_offset
            if v1 + vofs < 0:
                vofs = -v1
            if v2 + vofs >= 4095:
                vofs = v2 - 4095
            v1 += vofs
            v2 += vofs

        out += struct.pack("<I", id)
        out += struct.pack("<H", h2)
        out += struct.pack("<H", h1)
        out += struct.pack("<H", v2)
        out += struct.pack("<H", v1)
        out += struct.pack("<I", 0)

    if len(out) < VADJUST_LEN:
        out += bytes(VADJUST_LEN - len(out))
    return out

# -----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--out", dest="out_vadjust", metavar="FILE", help="output file")
    parser.add_argument("--pal5x", dest="pal_5x", action="store_true", default=False, help="make PAL crops for 5x scaling")
    parser.add_argument("--vofs", dest="v_offset", type=int, default=0, help="vertical offset")

    try:
        args = parser.parse_args()

        if args.out_vadjust:
            out = make_vadjust(args.pal_5x, args.v_offset)
            with open(args.out_vadjust, "wb") as f:
                f.write(out)
        return 0

    # except Exception as err:
    except IOError as err:
        print("error - {}".format(err))
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
