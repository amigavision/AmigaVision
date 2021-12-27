MegaAGS for Minimig-AGA_MiSTer
==============================

Setup:
------
- Copy the contents of the "games/Amiga" and "config" directories to the
  corresponding directories on MiSTer.

- When updating to a new version of the main HDF image do not overwrite
  "games/Amiga/MegaAGS-Saves.hdf", so old saved game data is carried over.

- If you prefer to configure the main settings manually, these are recommended
  settings used in the bundled minimig.cfg:

  df0: no disk
  df1: no disk
  Joystick Swap: OFF
  Drives:
    A600/A1200 IDE: On
    Fast-IDE (68020): On
    Primary Master: Fixed/HDD
                    games/Amiga/MegaAGS.hdf
    Primary Slave: Fixed/HDD
                    games/Amiga/MegaAGS-Saves.hdf
    Secondary Master: Disabled
    Secondary Slave: Disabled
    Floppy Disk Turbo: Off
  System:
    CPU: 68020
    D-Cache: OFF
    Chipset: AGA
    ChipRAM: 2M
    FastRAM: 384M
    SlowRAM: none
    CD32 Pad: ON
    ROM: games/Amiga/MegaAGS-Kickstart.rom
    HRTmon: disabled
  Audio & Video:
    TV Standard: PAL
    Scandoubler FX: Off
    Video area by: Blank
    Aspect ratio: Original
    Pixel Clock: Adaptive
    Scaling: Normal
    RTG Upscaling: Normal
    Stereo mix: 50%
    Audio Filter: Auto(LED)
    Model: A1200
    Paula Output: Normal

  There are a few additional configurations supplied, made for booting
  ADF floppy images. These are accessible from OSD -> Load configuration.
  Note that a "Guru Meditation" will often appear after a configuration
  is loaded. If so just use the OSD -> Reset function.

- Add the following recommended core overrides to MiSTer.ini (these settings
  are further explained in the next section):

[minimig]
video_mode_ntsc=8
video_mode_pal=9
vscale_mode=0
vsync_adjust=2
custom_aspect_ratio_1=40:27


Video Modes:
------------
Since many Amiga games only run properly at a 50Hz vertical refresh rate,
it's important to have both NTSC and PAL video modes set up in MiSTer.ini.
Note that while the recommended core setting is PAL, Amiga (and Minimig)
can change video modes on the fly. This is leveraged by the launcher to
dynamically apply per-game video mode settings. However, setting the core
option to PAL seems to benefit edge-case compatibility.

Another idiosyncrasy with the Minimig core is viewport cropping. By default
the full overscan area will be fed to the HDMI scaler, resulting in huge
borders. Fear not! MegaAGS leverages the "vadjust" feature of the core to
dynamically apply viewport settings on a per game basis. This depends on the
"shared folder" functionality, which is automatically enabled if the
"games/Amiga/shared" directory exists. So, make sure you copied all the
archive contents as described in the Setup section.

With dynamic vadjust enabled most titles will enjoy a nicely centered
viewport at a perfect 5x scale using 1080p output resolution, by cropping
the viewport to 216 lines. Games using more than 216 active video lines will
instead get a perfect 4x scale by applying a 270 line crop.

Now, we need to talk about Pixel Aspect Ratio (PAR). Most Amiga graphics
were drawn targeting a roughly square pixel display, if considering standard
low resolution mode. However, many American game were drawn using the 320x200px
mode stretched to cover a 4:3 display, yielding distinctly narrow pixels.
Using MiSTer's capability for setting up custom aspect ratios, it is possible
to quickly toggle between these PARs via OSD -> Audio & Video -> Aspect ratio.
Add the custom_aspect_ratio override to MiSTer.ini as specified above and
you will be able to toggle between "Original" and "40:27" settings (as well
as the fully useless "Full screen" setting).

"Original" will yield square pixels for full-height PAL titles, and the
sometimes correct narrow pixels for NTSC games. "40:27" will result in square
pixels for PAL (5X) titles and NTSC/PAL60 titles. As guidance, use these
settings depending on what video mode the launcher UI specifies:

PAL (4x)    Original
PAL (5x)    40:27
PAL60 (5x)  40:27
NTSC (5x)   40:27 or Original depending on title

Again, make sure to add the Minimig core overrides in MiSTer.ini as specified
in the previous section to enjoy the best HDMI output possible


Controls:
---------
While many games supports two or more buttons, Amiga games were generally
designed for one button joysticks. Consequently the feared "up to jump"
(or accelerate) control scheme is very common. If you are using a gamepad,
you might want to use MiSTer's controller mapping to bind the up direction
to both the D-pad and an extra button. Here's how:

- First, make sure to have CD32 controller mode enabled.
- Enter "Define joystick buttons" mode
- Map directions as usual
- Map the first three buttons (red, blue and yellow) to A, B and Y.
- The fourth button (green) is practically never used, and can be mapped
  to Select, R2/ZL or similar.
- Go ahead and map right/left triggers and play/pause.
- When asked to if you want to "setup alternative buttons", do so!
- Skip all choices except "up", which should be mapped to X.

While a keyboard and mouse isn't strictly necessary to play most action games,
it is definitely recommended for the full Amiga experience.


Save files:
-----------
For games with save functionality you need to quit the game using the DEL key
for the save data to be written to "disk", and thus the SD card.

In the "[ Options ]" menu you can choose between a few alternative quit key
options, which if set will override the preconfigured key. The active quit
key is displayed on the splash screen shown when a game is loading


CPU performance notes:
----------------------
The D-Cache option is essentially a turbo switch for the CPU, making it
perform on par with a 030 at 50MHz in many benchmarks. Unfortunately running
with it enabled introduces lots of subtle glitches in many (mostly older)
games and demos, so it's recommended is to leave it off as default.

On the other hand some titles, mostly 3D polygon games and demos, will
benefit greatly from the CPU boost D-Cache offers. So it's an option worth
experimenting with on a case by case basis.

Note that the glitches introduced with D-Cache on can sometimes clear up
by turning it off while Minimig is running. Other times they seem to stick
until reboot. The latter behavior is the case with, for example, Turrican II
and Grand Monster Slam (and many less significant titles).

The CPU D-Cache option is available in OSD -> System.


Workbench:
----------
From the launcher, you can hit the ESC key to exit into Workbench, the AmigaOS
graphical desktop environment.

You can explore the world's first multitasking 16-bit computer from 1985 with
the addition of a more modern desktop from 1992, AmigaOS 3.

To change from the default 640×256 resolution to something like 1280×720 or
1920×1080 for use with a 16:9 HD display, double-click the "Amiga" disk icon,
then "Prefs", then "ScreenMode" to select the resolution. Locate the ones
starting with "MiSTer:", and pick the one you prefer.


Non-working games:
------------------
About 10 games are currently not working due to CPU features not yet
implemented in the Minimig core. Over the past year compatibility has improved
a lot, and that trend is likely to continue. A few more titles do not work, or
are very glitchy, due to other inaccuracies. This will also hopefully improve
over time.


Custom scripts:
---------------
If you want to run additional scripts on startup, MegaAGS looks for a file
named Saves:custom-startup and runs it, so if you need to run scripts that
will survive upgrades of the main image, this is where to put them.


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
