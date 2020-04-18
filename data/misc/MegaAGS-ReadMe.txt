MegaAGS for Minimig-AGA_MiSTer
==============================

Setup:
------
- Copy MegaAGS.hdf, MegaAGS-Saves.hdf and MegaAGS-Kickstart.rom from the
  games/Amiga directory to the corresponding directory on MiSTer.

- When updating to a new version of the main HDF image, keep your old
  MegaAGS-Saves.hdf so any saved games are carried over.

- Copy minimig_vadjust.dat from the config directory to the corresponding
  directory on MiSTer. It contains viewport cropping settings to make nice
  5x (NTSC) and 4x (PAL) scaling ratios for 1080p output resolution possible.

- To make NTSC resolutions scale properly, you need to use 0.5x scale mode.
  If this is not already your default, add the following to your `MiSTer.ini`
  file:

  [Minimig]
  vscale_mode=2
   
- Either copy minimig.cfg from the config directory to the corresponding
  directory on MiSTer, or load the Minimig core and set up a profile with the
  following settings:

  df0: no disk
  df1: no disk
  Floppy disk turbo: Off
  Hard disks:
    A600/A1200 IDE: On
    Primary Master: Enabled
                    games/Amiga/MegaAGS.hdf
    Primary Slave: Enabled
                    games/Amiga/MegaAGS-Saves.hdf
    Secondary Master: Disabled
    Secondary Slave: Disabled
  CPU & Chipset:
    CPU: 68020
    D-Cache: OFF
    Chipset: AGA
    CD32 Pad: ON
    Joystick Swap: OFF
  Memory:
    CHIP: 2M
    FAST: 384M
    SLOW: none
    ROM: games/Amiga/MegaAGS-Kickstart.rom
    HRTmon: disabled
  Audio & Video:
    TV Standard: PAL
    Scandoubler FX: Off
    Video area by: Blank
    Aspect ratio: 4:3
    Stereo mix: 50%


Controls:
---------
Amiga games were generally designed for a one button joystick, which meant
that "up to jump" (or accelerate) is very common. And awkward. Buy have no
fear, with MiSTer's controller mapping it's easy to bind the up direction
to both the d-pad and an extra button. Here's how:

- First, make sure to have CD32 controller mode enabled.
- Enter "Define joystick buttons" mode
- Map directions as usual
- Map the first three buttons (red, Blue Yellow) to A, B and Y.
- The fourth button (green) is practically never used, and can be mapped
  to Select, ZL or similar.
- Go ahead and map Right and Left Triggers and Play/Pause.
- When asked to if you want to "setup alternative buttons", do so!
- Map Up to X, and skip all buttons except Up with the OSD button.

While a keyboard and mouse isn't strictly necessary to play most action games,
it is definitely recommended for the full Amiga experience.
Thank you for playing!


Video Modes:
------------
Since many Amiga games only run properly at a 50Hz vertical refresh rate,
make sure to have both NTSC and PAL video mode set up.

To set up 1080p output with 50/60Hz presets, add these platform overrides
to MiSTer.ini. Depending on how well your display deals with slightly
off-spec refresh frequencies and frequent mode changes you may want to
experiment with setting vsync_adjust to 1 or 0.

```
[minimig]
video_mode_ntsc=8
video_mode_pal=9
vsync_adjust=2
```

Also supplied is a minimig_vadjust.dat settings file, which contains crop
settings for the most common resolutions. We tried to find a good compromise
between small borders (while providing decent enough overscan for most games
not to cut content) and a nice scaling ratio at 1080p.
Copy the file into "/media/fat/config".

The menu will boot up in PAL mode and then change video modes depending on
the game selected. So, how you configure the video system in the OSD settings
doesn't matter but PAL is recommended since it will minimize the number of
video mode switches at boot.


Save files:
-----------
For games that save you need to quit (using the key displayed on the splash
screen shown when a game is loading) for the changes to be actually saved to
disk. The saves end up in "DH0:WHDSaves".

In the "[ Settings ]" menu you can choose between a few quit key options,
which if set will override the preconfigured (per-title) key.


Non-working games:
------------------
About 25-30 games are currently (2020-04-14) not working due to CPU features
not yet implemented in the Minimig core. Over the past year compatibility has
improved a lot, and that trend is likely to continue. A few more titles do not
work, or are very glitchy, due to other inaccuracies. This will also hopefully
improve over time.

The menu has a special "[ Issues ]" folder where the non-working titles (known
to us) are found. As more accurate versions of the Minimig core are released,
this folder can work as checklist for improved game compatibility.


Arcadia Systems:
----------------
Arcadia was an unsuccessful venture by Mastertronic to create an Amiga 500
based multi-game arcade system. Most titles released for the system have
been dumped and are available on the MegaAGS image. The games are not great
(to put it kindly), but it's a pretty interesting curiosity.

Button mapping:

P1 Start:    F1
P2 Start:    F2
Left Coin:   F3
Right Coin:  F4
Config:      F5

Player 1 uses joystick port 1, while Amiga software universally expect
mouse in port 1 and joystick in port 2. If using only one joystick, enable
the "Joy Swap" option in the Chipset menu to route the first MiSTer joypad
to port 1. It's also worth noting that all Arcadia games make use of a
2-button joystick.


Performance notes:
------------------
Some games will enjoy a nice performance boost with CPU D-Cache enabled, while
others will not work or run too fast. Especially 3D polygon games can benefit
from the faster CPU, so it's worth experimenting with the option on a case by
case basis. The D-Cache option is available in OSD -> CPU & Chipset.
