#!/usr/bin/env python3

import sys
import os
import argparse
import struct
import ags_util as util

# -----------------------------------------------------------------------------

modes = {
    0x000F25E4: "NTSC LowRes",
    0x010F25E4: "NTSC HiRes",
    0x020F25E4: "NTSC SuperHiRes",
    0x001E35E4: "NTSC LowRes Laced",
    0x011E35E4: "NTSC HiRes Laced",
    0x021E35E4: "NTSC SuperHiRes Laced",
    0x0011F5E4: "PAL LowRes",
    0x0111F5E4: "PAL HiRes",
    0x0211F5E4: "PAL SuperHiRes",
    0x0023D5E4: "PAL LowRes Laced",
    0x0123D5E4: "PAL HiRes Laced",
    0x0223D5E4: "PAL SuperHiRes Laced"
}

def read_chunks(f, length):
    while True:
        data = f.read(length)
        if not data: break
        yield data

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", metavar="FILE", type=lambda x: util.argparse_is_file(parser, x))
    try:
        args = parser.parse_args()

        with open(args.file, "rb") as f:
            for i, chunk in enumerate(read_chunks(f, 4*4)):
                if all([ b == 0 for b in chunk ]) is True:
                    continue

                mode = struct.unpack("<I", bytes(chunk[0:4]))[0]
                mode_name = modes[mode] if mode in modes else "unknown"

                r = (mode >> 24) & 0xff
                hs = mode & 0xfff
                vs = (mode >> 12) & 0xfff
                h1 = struct.unpack("<H", bytes(chunk[6:8]))[0]
                h2 = 4096 - struct.unpack("<H", bytes(chunk[4:6]))[0]
                v1 = struct.unpack("<H", bytes(chunk[10:12]))[0]
                v2 = 4096 - struct.unpack("<H", bytes(chunk[8:10]))[0]

                print("Mode: 0x{:08X} {} ({})".format(mode, r, mode_name))
                print("   H: {:4} [{:3} {:2}] => Width = {} => {} low res pixels".format(hs, h1, h2, hs-h1-h2, (hs-h1-h2)/4.0))
                print("   V: {:4} [{:3} {:2}] => Height = {} => {:2.3}x @ 1080p".format(vs, v1, v2, vs-v1-v2, 1080.0/(vs-v1-v2)))
                print()

        return 0

    # except Exception as err:
    except IOError as err:
        print("error - {}".format(err))
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
