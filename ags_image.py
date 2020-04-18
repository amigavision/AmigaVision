#!/usr/bin/env python3

# AGSImager: Image utility

import argparse
import os
import sys

from PIL import Image
import iff_ilbm as iff

# -----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--in_image", dest="in_image", required=True, metavar="FILE", help="input image")
    parser.add_argument("-o", "--out_iff", dest="out_iff", metavar="FILE", help="output IFF image")
    parser.add_argument("-c", "--colors", dest="colors", type=int, default=128, help="number of colors")

    try:
        args = parser.parse_args()

        # TODO: Add sizes to argparse
        dim_crop = (640, 512)
        dim_scaled = (320,256)
        dim_out = (320,128)

        colors = min(256, max(2, args.colors))
        img = Image.open(args.in_image).convert("RGB")

        # Normalize image to full "high-res interlace" resolution before cropping,
        # by doubling size in either dimension if smaller than crop dimension
        if img.size[0] < dim_crop[0]:
            img = img.resize((img.size[0] * 2, img.size[1]), Image.NEAREST)
        if img.size[1] < dim_crop[1]:
            img = img.resize((img.size[0], img.size[1] * 2), Image.NEAREST)

        # Find image "center of gravity" and crop around that
        box = img.getbbox()
        center = (int(box[0] + (box[2] - box[0]) / 2.0), int(box[1] + (box[3] - box[1]) / 2.0))
        img = img.crop((int(center[0] - dim_crop[0] / 2), int(center[1] - dim_crop[1] / 2), int(center[0] + dim_crop[0] / 2), int(center[1] + dim_crop[1] / 2)))

        # Resample
        img = img.resize(dim_scaled, Image.NEAREST)
        img = img.resize(dim_out, Image.ANTIALIAS)
        img = img.quantize(colors=colors, method=0, kmeans=4, dither=Image.NONE)

        # Save IFF
        if args.out_iff:
            with open(args.out_iff, "wb") as f:
                w, h = img.size
                f.write(iff.ilbm(w, h, img.load(), img.getpalette(), colors))
            #img.save(args.out_iff + ".png")

        return 0

    except IOError as err:
        print("error - {}".format(err))
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
