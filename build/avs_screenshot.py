#!/usr/bin/env python3

# AVSImager: IFF screenshot utility

# After scaling the input image to "high-res interlaced" pixel density,
# these crop/scaling operations are performed:
# - Crop to crop_size
# - Resample to scale_size (using nearest neighbour)
# - Optionally resample to resample_size (using aa interpolation)

# A CLI interface is also available. Example usage:
#
# Convert to canonical 404x280 hi-res with center-crop
# ./build/avs_screenshot.py --crop 640x512 --scale 404x280 --center_crop -i test.png -o test.iff
#
# Convert to 320x128 (squished height) with smart-crop, max 128 colors
# ./build/avs_screenshot.py --crop 640x512 --scale 320x256 --resample 320x128 --colors 128 -i test.png -o test.iff

import argparse
import sys

from PIL import Image

from repair_hires_palettes import black_padding_palette
from avs_artwork import validate_hires_thumbnail_size
import iff_ilbm

# -----------------------------------------------------------------------------

def iff_screenshot(path, colors, crop_sz, scale_sz, resample_sz=None, mode_id=0x29000, center_crop=False):
    resample_sz = resample_sz or scale_sz
    # Standard thumbnails are squashed to 320x128; all hi-res output is canonical.
    if tuple(resample_sz) != (320, 128):
        validate_hires_thumbnail_size(resample_sz, path)
    # Normalize image to full "high-res interlace" resolution before cropping,
    # by doubling size in either dimension if smaller than crop dimension
    img = Image.open(path).convert("RGB")
    if img.size[0] < crop_sz[0]:
        img = img.resize((img.size[0] * 2, img.size[1]), Image.Resampling.NEAREST)
    if img.size[1] < crop_sz[1]:
        img = img.resize((img.size[0], img.size[1] * 2), Image.Resampling.NEAREST)

    # Crop
    center = tuple(i // 2 for i in img.size)
    if not center_crop:
        box = img.getbbox()
        center = (int(box[0] + (box[2] - box[0]) / 2.0),
                  int(box[1] + (box[3] - box[1]) / 2.0))
    img = img.crop((int(center[0] - crop_sz[0] / 2), int(center[1] - crop_sz[1] / 2),
                    int(center[0] + crop_sz[0] / 2), int(center[1] + crop_sz[1] / 2)))

    # Resample
    img = img.resize(scale_sz, Image.Resampling.NEAREST)
    if scale_sz != resample_sz:
        img = img.resize(resample_sz, Image.Resampling.LANCZOS)
    # Keep indices 240-255 free for the launcher interface.
    img = img.quantize(colors=min(colors, 240), method=0, kmeans=4, dither=Image.Dither.NONE)

    # The launcher also displays the word-aligned padding at the right edge.
    img = black_padding_palette(img)
    return (iff_ilbm.ilbm(*img.size, img.load(), img.getpalette(), mode=mode_id, pack=1), img)

# -----------------------------------------------------------------------------
# CLI interface

def interpret_size(sz_str):
    sizes = tuple([int(s) for s in sz_str.replace("x", ",").replace("*", ",").split(",")])
    if len(sizes) != 2:
        raise IOError("invalid size argument (must be 2 integers): " + sz_str)
    if any([s < 1 for s in sizes]):
        raise IOError("invalid size argument (items must be greater than zero): " + sz_str)
    return sizes

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--in_image", dest="in_image", required=True, metavar="FILE", help="input image")
    parser.add_argument("-o", "--out_iff", dest="out_iff", metavar="FILE", help="output IFF image")
    parser.add_argument("-p", "--out_png", dest="out_png", metavar="FILE", help="output PNG image")
    parser.add_argument("-c", "--colors", dest="colors", type=int, default=240, help="number of colors (maximum 240; last 16 reserved for launcher)")
    parser.add_argument("--crop", dest="crop", type=str, default="640x512", help="crop size (in high-res interlaced point size)")
    parser.add_argument("--scale", dest="scale", type=str, default="404x280", help="scale size (nearest neighbour); final output must be 404x280 hi-res or 320x128 standard")
    parser.add_argument("--resample", dest="resample", type=str, default=None, help="resample size (anti aliased)")
    parser.add_argument("--center_crop", dest="center_crop", action="store_true", default=False, help="use center-crop (disable smart-crop)")
    parser.add_argument("--id", dest="screen_id", type=int, default=0x29000, help="set screen mode id")

    try:
        args = parser.parse_args()

        colors = min(240, max(2, args.colors))

        crop_sz = interpret_size(args.crop)
        scale_sz = interpret_size(args.scale)
        resample_sz = scale_sz
        if args.resample:
            resample_sz = interpret_size(args.resample)

        out, pil_img = iff_screenshot(args.in_image, colors, crop_sz, scale_sz, resample_sz, args.screen_id, args.center_crop)

        if args.out_iff:
            with open(args.out_iff, "wb") as f:
                f.write(out)
        if args.out_png:
            pil_img.save(args.out_iff + ".png")
        return 0

    except (IOError, ValueError) as err:
        print("error - {}".format(err))
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
