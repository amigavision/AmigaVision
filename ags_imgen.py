#!/usr/bin/env python3

# AGSImager: Hardcoded banner image generator

import io
import sys

from wand.color import Color
from wand.drawing import Drawing
from wand.image import Image
from PIL import Image as PILImage
import iff_ilbm as iff

WIDTH = 320
HEIGHT = 256
IMG_SRC_BASE = "data/img_src/"

# -----------------------------------------------------------------------------

# add gradient support for color arguments

def compose(operations):
    img = bg()
    for operation in operations if isinstance(operations, list) else [operations]:
        op = operation.pop("op", "nop")
        if op == "tx":
            img = tx(**operation, bg=img)
        elif op == "pi":
            img = pi(**operation, bg=img)
        elif op == "bg":
            img = bg(**operation)
    return img

# "bg" operation: solid color background
def bg(width=WIDTH, height=HEIGHT, color="#000"):
    return Image(width=width, height=height, background=Color(color))

# "tx" operation: single line text
# halign = "center", "left", "right"
# valign = "center", "top", "bottom"
def tx(txt, size=240, halign="center", valign="center", kerning=-1.0, font="display.otf", color="#ffffff", bg="#000000"):
    try:
        with Drawing() as drawing:
            img = bg if isinstance(bg, Image) else bg(color=bg)
            drawing.font = "content/fonts/{}".format(font)
            drawing.font_size = size
            drawing.fill_color = Color(color)
            drawing.text_kerning = kerning
            drawing.gravity = alignment_to_gravity(halign, valign)
            drawing.text(0, 0, txt)
            drawing(img)
            return img
    except ValueError:
        return 0

# "pi" operation: paste image from file
# scale = "fit" or number
# halign = "center", "left", "right"
# valign = "center", "top", "bottom"
def pi(path, scale="fit", halign="center", valign="center", mode="copy", bg="#000000"):
    try:
        with Drawing() as drawing:
            with Image(filename="{}{}".format(IMG_SRC_BASE, path)) as src:
                img = bg if isinstance(bg, Image) else bg(color=bg)
                img_ar = img.width / img.height
                src_ar = src.width / src.height

                (comp_width, comp_height) = (src.width, src.height)
                if isinstance(scale, float):
                    comp_width *= scale
                    comp_height *= scale
                elif isinstance(scale, str) and scale == "fit":
                    if src_ar > img_ar:
                        comp_width /= (src.width / img.width)
                        comp_height /= (src.width / img.width)
                    else:
                        comp_width /= (src.height / img.height)
                        comp_height /= (src.height / img.height)

                (comp_width, comp_height) = (round(comp_width), round(comp_height))

                if isinstance(halign, str) and halign == "left":
                    left = 0
                elif isinstance(halign, str) and halign == "right":
                    left = img.width - comp_width
                else:
                    left = round((img.width - comp_width) / 2)

                if isinstance(valign, str) and valign == "top":
                    top = 0
                elif isinstance(valign, str) and valign == "bottom":
                    top = img.height - comp_height
                else:
                    top = round((img.height - comp_height) / 2)

                drawing.composite(operator=mode, left=left, top=top, width=comp_width, height=comp_height, image=src)
                drawing(img)
                return img
    except ValueError:
        return 0

def alignment_to_gravity(halign="center", valign="center"):
    if isinstance(valign, str) and valign == "top":
        if isinstance(halign, str) and halign == "left":
            return "north_west"
        elif isinstance(halign, str) and halign == "right":
            return "north_east"
        else:
            return "north"
    elif isinstance(valign, str) and valign == "bottom":
        if isinstance(halign, str) and halign == "left":
            return "south_west"
        elif isinstance(halign, str) and halign == "right":
            return "south_east"
        else:
            return "south"
    else:
        if isinstance(halign, str) and halign == "left":
            return "west"
        elif isinstance(halign, str) and halign == "right":
            return "east"
        else:
            return "center"

def out_png(path, img, scale=(1, 1)):
    img = PILImage.open(io.BytesIO(img.make_blob("png"))).convert("RGB")

def out_iff(path, img, scale=(1, 0.5)):
    img = PILImage.open(io.BytesIO(img.make_blob("png"))).convert("RGB")
    img = img.resize((round(img.width * scale[0]), round(img.height * scale[1])), PILImage.Resampling.LANCZOS)
    img = img.quantize(colors=240, method=0, kmeans=4, dither=PILImage.Dither.NONE)

    w, h = img.size
    data = img.load()
    colors = max([data[x,y] for x in range(w) for y in range(h)]) + 1
    pal = img.getpalette()[:colors * 3]
    img_iff = iff.ilbm(w, h, img.load(), pal, 0x29000, 1)

    with open(path, "wb") as f:
        f.write(img_iff)

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    comp = compose({"op":"tx", "txt":"ASS"})
    comp.save(filename="out_op0_wnd.png")
    out_iff("out_op0_iff.png", comp)

    operations = [{"op":"tx", "txt":"ASS"}, {"op":"tx", "txt":"P*SS", "size":100, "color":"#f0f"}]
    compose(operations).save(filename="out_op1.png")

    operations = [{"op":"bg", "color":"#f00"}, {"op":"tx", "txt":"P*SS", "size":100, "color":"#f0f"}]
    compose(operations).save(filename="out_op2.png")

    operations = [{"op":"pi", "path":"chris_hülsbeck.jpg", "scale":1.0}]
    compose(operations).save(filename="out_pi1.png")

    operations = [
        {"op":"pi", "path":"chris_hülsbeck.jpg", "scale":2.0, "halign":"right", "valign":"top"},
        {"op":"tx", "txt":"chris!", "size":100, "color":"#f0f"}
    ]
    compose(operations).save(filename="out_pi2.png")

    operations = [
        {"op":"pi", "path":"chris_hülsbeck.jpg", "halign":"right"},
        {"op":"tx", "txt":"chrijs!", "size":100, "color":"#f0f", "halign":"left", "valign":"bottom"}
    ]
    compose(operations).save(filename="out_pi3.png")

    operations = [
        {"op":"pi", "path":"chris_hülsbeck_wide.png", "valign":"bottom"},
        {"op":"tx", "txt":"chris!", "size":100, "color":"#f0f", "halign":"right", "valign":"top"}
    ]
    compose(operations).save(filename="out_pi4.png")

    sys.exit(0)
