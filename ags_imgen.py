#!/usr/bin/env python3

# AGSImager: Hardcoded banner image generator

import sys

from wand.color import Color
from wand.drawing import Drawing
from wand.image import Image

# -----------------------------------------------------------------------------

# add gradient support for color arguments

def big_letters(str, size=240, kerning=-1.0, color="#ffffff", bg_color="#000000"):
    try:
        w = 320
        h = 256
        with Drawing() as drawing:
            img = Image(width=w, height=h, background=Color(bg_color))
            drawing.font = "content/fonts/display.otf"
            drawing.font_size = size
            drawing.fill_color = Color(color)
            drawing.text_alignment = "center"
            drawing.text_kerning = kerning
            metrics = drawing.get_font_metrics(img, str)
            drawing.text(round(w / 2), round((h / 2) + ((metrics.ascender + (metrics.descender / 2)) / 2)), str)
            drawing(img)
            return img
    except ValueError:
        return 0

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
    big_letters("A").save(filename="out_A.png")
    big_letters("1987", size=112).save(filename="out_1987.png")
    #emoji("😻", color="#ffffff").save("out_emoji.png")
    #emoji_roundrect("🤮", color="#000000").save("out_emojirect.png")
    sys.exit(0)
