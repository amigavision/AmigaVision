MegaAGS for Minimig-AGA_MiSTer
==============================

Important notice: Since 2020.07.01 releases include a new custom made kickstart
ROM and makes use of the new shared folder functionality for game data backups.
If upgrading from an earlier release it is recommended to remove all old files
before upgrading.

Also, always make sure you run the latest MiSTer main and Minimig core.

Setup:
------
- Copy MegaAGS.hdf, MegaAGS-Kickstart.rom and the "shared" directory from
  the Amiga directory to /games/Amiga on the MiSTer SD card.

- Copy minimig.cfg and minimig_vadjust.dat from the config directory to the
  corresponding directory on MiSTer. The vadjust file contains viewport crop
  settings to enable perfect 5x (NTSC) and 4x (PAL) scaling ratios at 1080p.

  If you prefer to configure the main settings manually, these are recommended
  settings used in the bundled minimig.cfg:

  df0: no disk
  df1: no disk
  Floppy disk turbo: Off
  Hard disks:
    A600/A1200 IDE: On
    Primary Master: Enabled
                    games/Amiga/MegaAGS.hdf
    Primary Slave: Disabled
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

- Add the following recommended core overrides to MiSTer.ini (these settings
  are further explained in the "Video Modes" paragraph):

  [minimig]
  video_mode_ntsc=8
  video_mode_pal=9
  vscale_mode=2
  vsync_adjust=2


CPU performance notes:
----------------------
Some games and demos, particularily if released in 1993 or later, will enjoy
a substantial performance improvement with CPU D-Cache enabled.
Especially 3D polygon games can benefit from the CPU boost, while others may
run too fast or not work at all, so it's worth experimenting with the option
on a case by case basis.
The CPU D-Cache option is available in OSD -> CPU & Chipset.


Controls:
---------
Amiga games were generally designed for a one button joystick, which meant
that "up to jump" (or accelerate) is very common. And awkward. But, have no
fear, with MiSTer's controller mapping it's easy to bind the up direction
to both the d-pad and an extra button. Here's how:

- First, make sure to have CD32 controller mode enabled.
- Enter "Define joystick buttons" mode
- Map directions as usual
- Map the first three buttons (red, blue and yellow) to A, B and Y.
- The fourth button (green) is practically never used, and can be mapped
  to Select, ZL or similar.
- Go ahead and map Right and Left Triggers and Play/Pause.
- When asked to if you want to "setup alternative buttons", do so!
- Map Up to X, and skip all buttons except Up with the OSD button.

While a keyboard and mouse isn't strictly necessary to play most action games,
it is definitely recommended for the full Amiga experience.
Thank you for playing!


Save files:
-----------
For games with save functionality you need to quit the game using the DEL key
for the save data to be written to the SD card.
The save directory is Amiga:WHDSaves.

In the "[ Options ]" menu there are commands that will backup and restore the
save data to the MiSTer shared folder.

In the "[ Options ]" menu you can also choose between a few alternative quit
key options, which if set will override the preconfigured key. The active
quit key is displayed on the splash screen shown when a game is loading


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


Non-working games:
------------------
About 20 games are currently not working due to CPU features not yet
implemented in the Minimig core. Over the past year compatibility has improved
a lot, and that trend is likely to continue. A few more titles do not work, or
are very glitchy, due to other inaccuracies. This will also hopefully improve
over time.


Workbench:
----------
From the launcher, you can hit the ESC key to exit into Workbench, the AmigaOS
graphical desktop environment.

You can explore the world's first multitasking 16-bit computer from 1985 with
the addition of a more modern desktop from 1992, AmigaOS 3.

Amiga, with the AGA chipset onwards (1992) is capable of using HD resolutions.
The HD720 monitor driver is included, and will make it possible to run the
Amiga Workbench at 1280×720 pixels.

To change from the default 640×256 resolution to 1280×720, double-click the
"Amiga" disk icon, then "Prefs", then "ScreenMode" to select the resolution.
You want to locate the ones starting with "HD720:", and pick the one you
prefer. The Amiga UI is designed for a 2:1 pixel ratio in general, so
1280×360 would be the most accurate way to do that. You can also run at
1280×720, especially if you add a modern icon set to it that is designed for
square pixel icons.

Then, trigger the MiSTer menu, and select Audio & Video -> Aspect Ratio
-> 16:9.


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
