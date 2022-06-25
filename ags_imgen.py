#!/usr/bin/env python3

# AGSImager: Hardcoded banner image generator

import sys

from PIL import Image, ImageColor, ImageDraw, ImageFont

# -----------------------------------------------------------------------------

# add gradient support for color arguments

def big_letters(str, size=200, color="#ffffff", bg_color="#000000"):
    try:
        w = 320
        h = 256
        bg = ImageColor.getrgb(bg_color)
        fg = ImageColor.getrgb(color)

        font = ImageFont.truetype("content/fonts/display.ttf", size)
        im = Image.new("RGB", (w, h), bg)
        d = ImageDraw.Draw(im)

        d.text((round(w / 2), round((h / 2) + (size / 2.8))), str, fill=fg, anchor="ms", font=font)
        return im
    except ValueError:
        return 0

def emoji(str, size=180, color="#ffffff", bg_color="#000000"):
    try:
        w = 320
        h = 256
        bg = ImageColor.getrgb(bg_color)
        fg = ImageColor.getrgb(color)

        font = ImageFont.truetype("content/fonts/emoji.ttf", size)
        im = Image.new("RGB", (w, h), bg)
        d = ImageDraw.Draw(im)

        d.text((round(w / 2), round(h / 2)), str, fill=fg, anchor="mm", font=font)
        return im
    except ValueError:
        return 0

def emoji_roundrect(str, size=220, sym_size=None, color="#000000", rect_color="#ffffff", bg_color="#000000"):
    # ImageDraw.rounded_rectangle doesn't antialias, so let's use an emoji for the shape...
    try:
        w = 320
        h = 256
        bg = ImageColor.getrgb(bg_color)
        fg = ImageColor.getrgb(color)
        rc = ImageColor.getrgb(rect_color)
        sym_size = sym_size if sym_size is not None else round(size * 0.75)

        rect_font = ImageFont.truetype("content/fonts/emoji.ttf", size)
        font = ImageFont.truetype("content/fonts/emoji.ttf", sym_size)
        im = Image.new("RGB", (w, h), bg)
        d = ImageDraw.Draw(im)

        d.text((round(w / 2), round(h / 2)), "🔼", fill=rc, anchor="mm", font=rect_font)
        d.text((round(w / 2), round(h / 2)), "🔺", fill=rc, anchor="mm", font=rect_font)
        d.text((round(w / 2), round(h / 2)), str, fill=fg, anchor="mm", font=font)
        return im
    except ValueError:
        return 0

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    big_letters("A").save("out_bigletters.png")
    emoji("😻", color="#ffffff").save("out_emoji.png")
    emoji_roundrect("🤮", color="#000000").save("out_emojirect.png")
    sys.exit(0)
