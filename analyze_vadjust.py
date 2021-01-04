#!/usr/bin/env python3

# AGSImager: analyze screenshot to decide optimum vadjust

import sys
import os
import argparse

from PIL import Image
import ags_util as util

# -----------------------------------------------------------------------------

VIEWPORT_HEIGHT = 216
REF_PAL5 = 21

def analyze(path):
    img = Image.open(path).convert("RGB")

    # list lines containing only background color
    bgcolor = img.getpixel((0,0))
    bglines = []
    for y in range(0, img.height):
        bglines.append(all([img.getpixel((x,y)) == bgcolor for x in range(0, img.width)]))

    # get height of blank top and bottom segments
    ftop = 0
    for l in bglines:
        if l: ftop += 1
        else: break
    fbottom = img.height
    for l in reversed(bglines):
        if l: fbottom -= 1
        else: break
    fheight = fbottom - ftop

    top = ftop >> 1
    bottom = fbottom >> 1
    height = bottom - top
    margin = (VIEWPORT_HEIGHT - height) >> 1

    if (ftop != top << 1) or (fbottom != bottom << 1):
        print("warning: progressive bounding box not integral")

    stats = (top, bottom, height, margin)
    pal5_vofs = top - REF_PAL5

    return (pal5_vofs, stats)

# -----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image", metavar="FILE", help="image")

    try:
        args = parser.parse_args()

        if not util.is_file(args.image):
            raise IOError("file doesn't exist: " + args.image)
            return 1

        print(analyze(args.image))
        #print(analyze(args.image)[0])
        return 0

    # except Exception as err:
    except IOError as err:
        print("error - {}".format(err))
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
