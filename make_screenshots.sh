#!/bin/bash

for f in $1/*.png; do
    [ -f "$f" ] || break
    echo "Converting $f"
    ./ags_screenshot.py --crop 640x512 --scale 320x256 --resample 320x128 --colors 128 -i "$f" -o "$f".iff -p "$f".out.png
done
