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
    Aspect ratio: 40:27
    Pixel Clock: Adaptive
    Scaling: Normal
    RTG Upscaling: Normal
    Stereo mix: 50%
    Audio Filter: Auto(LED)
    Model: A500
    Paula Output: PWM

- Add the following recommended core overrides to MiSTer.ini (these settings
  are further explained in the next section):

[minimig]
video_mode_ntsc=8
video_mode_pal=9
vsync_adjust=1
custom_aspect_ratio_1=40:27


Video Modes:
------------
First, the optimal vsync_adjust setting will depend on your HDMI display.
A setting of 2 ensures the lowest possible latency, but it may come at the
cost of a short period of no video or audio on video mode changes - something
Amiga games and demos do a lot. Setting vsync_adjust to 1 introduces a buffer
that will smooth over most of these changes.

A unique feature of the Minimig core is arbitrary viewport cropping. By
default the full overscan area will be fed to the HDMI scaler, resulting in
huge borders for most content. Fear not! MegaAGS leverages the "vadjust"
feature of the core to dynamically apply viewport settings on a per game
basis. This depends on the "shared folder" functionality, which is enabled
if the "games/Amiga/shared" directory exists. So, make sure you copied all
the archive contents as described in the Setup section.

Also note that the dynamic cropping *only* applies if you are using 1080p
output. Most Amiga games fit on the screen using 5× zoom in this resolution.
Any other resolution or analog output is *not* affected by dynamic viewport
cropping.

With dynamic vadjust enabled most titles will enjoy a nicely centered
viewport at a perfect 5× scale using 1080p output resolution, by cropping
the viewport to 216 lines. Games using more than 216 active video lines will
instead get a perfect 4× scale by applying a 270 line crop.

Now, we need to talk about Pixel Aspect Ratio (PAR). Most Amiga graphics
were drawn targeting a roughly square pixel display, if considering standard
low resolution mode. However, some American game were drawn using the 320x200px
mode stretched to cover a 4:3 display, yielding distinctly narrow pixels.
Using MiSTer's capability for setting up custom aspect ratios, it is possible
to quickly toggle between these PARs via OSD -> Audio & Video -> Aspect ratio.
Add the custom_aspect_ratio override to MiSTer.ini as specified above and
you will be able to toggle between "Original" and "40:27" settings (as well
as the fully useless "Full screen" setting).

"Original" will yield square pixels for full-height PAL titles, and the
sometimes correct narrow pixels for NTSC games. "40:27" will result in square
pixels for PAL (5×) titles and NTSC/PAL60 titles. As guidance, use these
settings depending on what video mode the launcher UI specifies:

4×PAL      Original
5×PAL      40:27
5×PAL60    40:27
5×NTSC     40:27 or Original depending on title

Again, make sure to add the Minimig core overrides in MiSTer.ini as specified
in the previous section to enjoy the best HDMI output possible, and make sure
you have set MiSTer to output in 1080p resolution.


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
IMPORTANT: For games with save functionality you need to quit the game using
the DEL key for the save data to be written to "disk", and thus the SD card.
You will lose your save games if you don't exit the game after saving!

In the "[ Options ]" menu you can choose between a few alternative quit key
options, which if set will override the preconfigured key. The active quit
key is displayed on the splash screen shown when a game is loading.


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

To change from the default 640×200 resolution to something like 1280×720 or
1920×1080 for use with a 16:9 HD display, hold down the right mouse button and
select your preferred resolution from the ScreenMode menu. 540p is a nice,
usable screen resolution that just doubles every pixel on a 1080p display.


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
