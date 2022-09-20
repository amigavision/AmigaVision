#!/usr/bin/env python3

# AGSImager: Hardcoded banner image generator

import io
import sys

from wand.color import Color
from wand.drawing import Drawing
from wand.image import Image
from PIL import Image as PILImage
import iff_ilbm as iff

# -----------------------------------------------------------------------------

# add gradient support for color arguments

def compose(operations):
    img = bg()
    for operation in operations if isinstance(operations, list) else [operations]:
        op = operation.pop("op", "nop")
        if op == "tx":
            img = tx(**operation, bg=img)
        elif op == "bg":
            img = bg(**operation)
    return img

def bg(width=320, height=256, color="#000"):
    return Image(width=width, height=height, background=Color(color))

def tx(str, size=240, kerning=-1.0, color="#ffffff", bg="#000000"):
    try:
        with Drawing() as drawing:
            img = bg if isinstance(bg, Image) else bg(color=bg)
            drawing.font = "content/fonts/display.otf"
            drawing.font_size = size
            drawing.fill_color = Color(color)
            drawing.text_alignment = "center"
            drawing.text_kerning = kerning
            metrics = drawing.get_font_metrics(img, str)
            drawing.text(round(img.width / 2), round((img.height / 2) + ((metrics.ascender + (metrics.descender / 2)) / 2)), str)
            drawing(img)
            return img
    except ValueError:
        return 0

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

#def emoji(str, size=180, color="#ffffff", bg_color="#000000"):
#    try:
#        w = 320
#        h = 256
#        bg = ImageColor.getrgb(bg_color)
#        fg = ImageColor.getrgb(color)
#
#        font = ImageFont.truetype("content/fonts/emoji.ttf", size)
#        im = Image.new("RGB", (w, h), bg)
#        d = ImageDraw.Draw(im)
#
#        d.text((round(w / 2), round(h / 2)), str, fill=fg, anchor="mm", font=font)
#        return im
#    except ValueError:
#        return 0

#def emoji_roundrect(str, size=220, sym_size=None, color="#000000", rect_color="#ffffff", bg_color="#000000"):
#    # ImageDraw.rounded_rectangle doesn't antialias, so let's use an emoji for the shape...
#    try:
#        w = 320
#        h = 256
#        bg = ImageColor.getrgb(bg_color)
#        fg = ImageColor.getrgb(color)
#        rc = ImageColor.getrgb(rect_color)
#        sym_size = sym_size if sym_size is not None else round(size * 0.75)
#
#        rect_font = ImageFont.truetype("content/fonts/emoji.ttf", size)
#        font = ImageFont.truetype("content/fonts/emoji.ttf", sym_size)
#        im = Image.new("RGB", (w, h), bg)
#        d = ImageDraw.Draw(im)
#
#        d.text((round(w / 2), round(h / 2)), "🔼", fill=rc, anchor="mm", font=rect_font)
#        d.text((round(w / 2), round(h / 2)), "🔺", fill=rc, anchor="mm", font=rect_font)
#        d.text((round(w / 2), round(h / 2)), str, fill=fg, anchor="mm", font=font)
#        return im
#    except ValueError:
#        return 0

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    comp = compose({"op":"tx", "str":"ASS"})
    comp.save(filename="out_op0_wnd.png")
    out_iff("out_op0_iff.png", comp)

    operations = [{"op":"tx", "str":"ASS"}, {"op":"tx", "str":"P*SS", "size":100, "color":"#f0f"}]
    compose(operations).save(filename="out_op1.png")

    operations = [{"op":"bg", "color":"#f00"}, {"op":"tx", "str":"P*SS", "size":100, "color":"#f0f"}]
    compose(operations).save(filename="out_op2.png")

    sys.exit(0)
