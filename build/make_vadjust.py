#!/usr/bin/env python3

# AGSImager: vadjust.dat creation utility

# v_shift expressible range:
#   NTSC-5X: -16 ... 9
#   NTSC-6X: -16 ... 45
#   PAL-4X:  -11 ... 5
#   PAL-5X:  -11 ... 59
#   PAL-6X:  -11 ... 95

# Pixel aspect ratios to support:
# 1:1   = 1.0
# 16:15 = 1.06667
# 5:6   = 0.83333
# https://eab.abime.net/showthread.php?t=50015
# http://coppershade.org/articles/More!/Topics/Correct_Amiga_Aspect_Ratio/

# Minimig viewport width:
# (offsets in SHR pixels -> reported width)
#   0 : 0   -> 754 HR pixels at max overscan (377)
#  76 : 0   -> 716 HR pixels at max centered overscan (358)
# 152 : 76  -> 640 HR pixels at minimum size without underscan

# Base resolution: 320x216 @ 5X
#  - 1600x1080 @ 1:1 PAR, 40:27 DAR
#  - 1706x1080 @ 16:15 PAR, ~74:47 DAR

# Possible display aspect ratios:
# 40:27 = 1.4814814815 (1:1 PAR for 5X)
# 74:47 = 1.5744680851 (16:15 PAR for 5X, too wide for 4X)
# 75:49 = 1.5306122448 (halfway point between the two above)
# https://morf77.pythonanywhere.com/ar

# 4X PAL mode if using 1600x1080:
# Reverse adjusted for 16:15 -> 1500 ~> 748x270 (hires)
# 754-748 = 6 -> 0:12 SHR crop

# 5:6 PAR for 5X at 40:27 (Jim Sachs mode)
# 1600x1080 -> 320 -> *(5/6) ~= 268
# Add 52 LR pixels of overscan -> 208 SHR pixels -> 132:76 SHR crop -> 0:20

# Older notes:
# 4X crop with max centered overscan -> 358x270
# Enlarged to 1080p -> 1432x1080
# Adjusted for 16:15 PAR -> 1528x1080
#
# -> Optimal 5x crop in 1528x1080 for 16:15 PAR
# 1432 horizontal pixels / 5 -> 286 -> Way too much underscan

import argparse
import struct
import sys

# -----------------------------------------------------------------------------
VSHIFT_MIN = -16
VSHIFT_MAX = 96

VADJUST_LEN = 1024

BASE_HL = 152
BASE_HR = 76
PAL4_HL = 12
PAL4_HR = 0
SACHS_HL = 20
SACHS_HR = 0

PAL4_HL_EXPAND = 0
PAL4_HR_EXPAND = 0

base_values = {
    "pal": {
        4: ((PAL4_HL, PAL4_HR), (11, 6)),
        5: ((BASE_HL, BASE_HR), (11, 60)),
        6: ((BASE_HL, BASE_HR), (11, 96)),
    },
    "ntsc": {
        5: ((BASE_HL, BASE_HR), (16, 10)),
        6: ((BASE_HL, BASE_HR), (16, 46)),
    }
}

# mode, name, ntsc, laced
modes = [
    (0x000F25E4, "NTSC LowRes", True, False),
    (0x000F15E4, "NTSC LowRes--", True, False),
    (0x010F25E4, "NTSC HiRes", True, False),
    (0x000F15E4, "NTSC HiRes--", True, False),
    (0x020F25E4, "NTSC SuperHiRes", True, False),
    (0x020F15E4, "NTSC SuperHiRes--", True, False),
    (0x001E35E4, "NTSC LowRes Laced", True, True),
    (0x001E25E4, "NTSC LowRes Laced--", True, True),
    (0x011E35E4, "NTSC HiRes Laced", True, True),
    (0x011E25E4, "NTSC HiRes Laced--", True, True),
    (0x021E35E4, "NTSC SuperHiRes Laced", True, True),
    (0x021E25E4, "NTSC SuperHiRes Laced--", True, True),
    (0x0011F5E4, "PAL LowRes", False, False),
    (0x0011E5E4, "PAL LowRes--", False, False),
    (0x0111F5E4, "PAL HiRes", False, False),
    (0x0111E5E4, "PAL HiRes--", False, False),
    (0x0211F5E4, "PAL SuperHiRes", False, False),
    (0x0211E5E4, "PAL SuperHiRes--", False, False),
    (0x0023D5E4, "PAL LowRes Laced", False, True),
    (0x0023C5E4, "PAL LowRes Laced--", False, True),
    (0x0123D5E4, "PAL HiRes Laced", False, True),
    (0x0123C5E4, "PAL HiRes Laced--", False, True),
    (0x0223D5E4, "PAL SuperHiRes Laced", False, True),
    (0x0223C5E4, "PAL SuperHiRes Laced--", False, True)
 ]

def make_vadjust(scale=0, v_shift=0, sachs=False):
    out = bytes()

    for mode in modes:
        id = mode[0]
        ntsc = bool(mode[2])
        lace = bool(mode[3])

        # get base values
        if ntsc:
            sf = scale if scale in [5, 6] else 5
            ((l, r), (t, b)) = base_values["ntsc"][sf]
            if sachs and sf == 5:
                (l, r) = (SACHS_HL, SACHS_HR)
        else:
            sf = scale if scale in [4, 5, 6] else 4
            ((l, r), (t, b)) = base_values["pal"][sf]
            if sachs and sf == 5:
                (l, r) = (SACHS_HL, SACHS_HR)
        # interlace adjustment
        if lace:
            b -= 1
        # negate right/bottom offset
        r = 4096 - r
        b = 4096 - b
        # adjust for vertical shift
        if v_shift != 0:
            vsh = v_shift
            if t + vsh < 0:
                vsh = -t
            if b + vsh > 4095:
                vsh = 4095 - b
            t += vsh
            b += vsh

        out += struct.pack("<I", id)
        out += struct.pack("<H", r)
        out += struct.pack("<H", l)
        out += struct.pack("<H", b)
        out += struct.pack("<H", t)
        out += struct.pack("<I", 0)

    if len(out) < VADJUST_LEN:
        out += bytes(VADJUST_LEN - len(out))
    return out

# -----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--out", dest="out_vadjust", metavar="FILE", help="output file")
    parser.add_argument("--scale", dest="scale", type=int, default=0, help="create viewport crops with forced scale factor (5 or 6)")
    parser.add_argument("--vshift", dest="v_shift", type=int, default=0, help="set vertical shift (positive values move visible image up)")
    parser.add_argument("--sachs", dest="sachs", action="store_true", default=False, help="jim sachs mode (5:6 PAR for 5X scale)")

    try:
        args = parser.parse_args()

        if args.out_vadjust:
            out = make_vadjust(scale=args.scale, v_shift=args.v_shift, sachs=args.sachs)
            with open(args.out_vadjust, "wb") as f:
                f.write(out)
        return 0

    # except Exception as err:
    except IOError as err:
        print("error - {}".format(err))
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
