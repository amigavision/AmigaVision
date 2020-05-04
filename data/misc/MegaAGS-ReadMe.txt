MegaAGS for Minimig-AGA_MiSTer
==============================

Setup:
------
- Copy MegaAGS.hdf, MegaAGS-Saves.hdf and MegaAGS-Kickstart.rom from the
  Amiga directory to /games/Amiga the corresponding directory on MiSTer.

- When updating to a new version of the main HDF image, keep your old
  MegaAGS-Saves.hdf so any saved games are carried over.

- Copy minimig_vadjust.dat from the config directory to the corresponding
  directory on MiSTer. It contains viewport cropping settings to make nice
  5x (NTSC) and 4x (PAL) scaling ratios for 1080p output resolution possible.

- Add the following core overrides to MiSTer.ini (these settings are further
  explained in the "Video Modes" paragraph):

  [minimig]
  video_mode_ntsc=8
  video_mode_pal=9
  vscale_mode=2
  vsync_adjust=2

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
that "up to jump" (or accelerate) is very common. And awkward. But, have no
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
it's important to have both NTSC and PAL video modes set up in MiSTer.ini.

Another idiosyncrasy with the Minimig core is viewport cropping. By default
the full overscan area will be fed to the HDMI scaler, resulting in huge
borders. Fear not! Also supplied is a minimig_vadjust.dat settings file, which
contains crop settings for all the common resolutions. With this file copied
to the /config directory, regular NTSC and PAL resolutions will be output at
216 and 270 lines respectively, thus being perfectly suited for integer
scaling at a 1080p output resolution.

To also make interlaced resolutions fill the screen, however, you still need
to enable 0.5x scale mode. In summary, these are the recommended MiSTer.ini
settings:

```
[minimig]
video_mode_ntsc=8
video_mode_pal=9
vscale_mode=2
vsync_adjust=2
```

Depending on how well your display deals with slightly off-spec refresh
frequencies and frequent mode changes you may need to experiment with setting
vsync_adjust to 1 or 0, instead of the ideal setting of 2.


Save files:
-----------
For games that save you need to quit (using the key displayed on the splash
screen shown when a game is loading) for the changes to be actually saved to
disk. The saves end up in "DH0:WHDSaves".

In the "[ Settings ]" menu you can choose between a few quit key options,
which if set will override the preconfigured (per-title) key.


Non-working games:
------------------
About 20 games are currently not working due to CPU features not yet
implemented in the Minimig core. Over the past year compatibility has improved
a lot, and that trend is likely to continue. A few more titles do not work, or
are very glitchy, due to other inaccuracies. This will also hopefully improve
over time.


Workbench:
----------
From the launcher, you can hit the Esc key to exit into Workbench, the Amiga's
desktop system.

You can explore the world's first multitasking 16-bit computer from 1985 with
the addition of a more modern desktop from 1992.

Amigas with the AGA chipset onwards (1992) is capable of using HD resolutions.
The "HD720" monitor driver is included, and will make it possible to run the
Amiga Workbench at 1280×720 pixels. 

To change from the default 640×256 resolution to 1280×720, double-click the
"Amiga" disk icon, then "Prefs", then "ScreenMode" to select the resolution.
You want to locate the ones starting with "HD720:", and pick the one you 
prefer. The Amiga UI is designed for a 2:1 pixel ratio in general, so 
1280×360 would be the most accurate way to do that. You can also run at 
1280×720, especially if you add a modern icon set to it that is built for 
1×1 icons.


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
