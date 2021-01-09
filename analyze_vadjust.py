#!/usr/bin/env python3

# AGSImager: analyze screenshot to decide optimum vadjust

import sys
import os
import argparse

from PIL import Image
import ags_util as util

# -----------------------------------------------------------------------------

PAL5_VIEWPORT_HEIGHT = 216
PAL5_FUDGE = 20
PAL4_VIEWPORT_HEIGHT = 270
PAL4_FUDGE = 16

def analyze(path):
    img = Image.open(path).convert("RGB")
    if img.height != 572:
        print("warning: image height is not 572 (use 'full' screenshot)")

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
    if (ftop != top << 1) or (fbottom != bottom << 1):
        print("warning: progressive bounding box not integral")

    height = bottom - top
    pal5_margin = (PAL5_VIEWPORT_HEIGHT - height) >> 1
    pal4_margin = (PAL4_VIEWPORT_HEIGHT - height) >> 1
    pal5_vofs = top - PAL5_FUDGE
    pal4_vofs = top - PAL4_FUDGE

    stats = {
        "top": top, "bottom": bottom, "height": height,
        "pal5_margin": pal5_margin, "pal5_vofs": pal5_vofs,
        "pal4_margin": pal4_margin, "pal4_vofs": pal4_vofs
    }

    if pal5_margin < 0:
        r = "mode: pal4, v_offset: {}".format(pal4_vofs)
    else:
        r = "mode: pal5, v_offset: {}".format(pal5_vofs)

    return (stats,r)

# -----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image", metavar="FILE", help="image")
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", default=False, help="verbose output")

    try:
        args = parser.parse_args()

        if not util.is_file(args.image):
            raise IOError("file doesn't exist: " + args.image)
            return 1

        (stats, r) = analyze(args.image)
        if args.verbose:
            print(stats,"->")
        print(r)
        return 0

    # except Exception as err:
    except IOError as err:
        print("error - {}".format(err))
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
