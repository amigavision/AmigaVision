MegaAGS for Minimig-AGA_MiSTer
==============================

Setup:
------
- Copy MegaAGS.hdf, MegaAGS-Saves.hdf, MegaAGS-Kickstart.rom and the "shared"
  directory from the Amiga directory to /games/Amiga on the MiSTer SD card.

- When updating to a new version of the main HDF image, keep your old
  MegaAGS-Saves.hdf so any saved games are carried over.

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
    Primary Slave: Enabled
                    games/Amiga/MegaAGS-Saves.hdf
    Secondary Master: Disabled
    Secondary Slave: Disabled
  CPU & Chipset:
    CPU: 68020
    D-Cache: ON
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
With the D-Cache option enabled the "020" CPU core will enjoy substantial
performance improvements, on par with a 030 at 50MHz in many benchmarks.
Since most WHDL installs include patches to counter bugs introduced when
running games and demos on a much faster CPU than originally intended,
having the option on is highly recommended. Not only will booting, browsing
the menu system and running the Workbench be faster - many games will
benefit too, especially almost any involving 3D polygon rendering.
Still, some titles may have bugs or simply run too fast, in which case it's
worth experimenting with turning the option off.
The CPU D-Cache option is available in OSD -> CPU & Chipset.


Controls:
---------
Amiga games were generally designed for one button joysticks, which meant
that "up to jump" (or accelerate) is very common. If you are using a game pad,
you might want to use MiSTer's controller mapping to bind the up direction to
both the D-pad and an extra button. Here's how:

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
for the save data to be written to "disk", and thus the SD card.

In the "[ Settings ]" menu you can choose between a few alternative quit key
options, which if set will override the preconfigured key. The active quit
key is displayed on the splash screen shown when a game is loading

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

[minimig]
video_mode_ntsc=8
video_mode_pal=9
vscale_mode=2
vsync_adjust=2

Depending on how well your display deals with slightly off-spec refresh
frequencies and frequent mode changes you may need to experiment with setting
vsync_adjust to 1 or 0, instead of the ideal setting of 2.


Non-working games:
------------------
About 10 games are currently not working due to CPU features not yet
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

To change from the default 640×256 resolution to something like 1280×720 or
1920×1080 for use with a 16:9 HD display, double-click the "Amiga" disk icon,
then "Prefs", then "ScreenMode" to select the resolution.

You want to locate the ones starting with "MiSTer:", and pick the one you
prefer.

If you chose a 16:9 aspect ratio resolution, trigger the MiSTer menu, and
select Audio & Video -> Aspect Ratio -> 16:9.


Internet:
---------
The Amiga was also one of the early computers to support connecting to the
Internet. The image includes some of the basic tools:

* IBrowse - web browser
* AmFTP - FTP client
* AmIRC - IRC client
* AmTelnet - telnet and ssh client
* YAM - email client

As well as some supporting tools:
* Miami - TCP/IP stack
* AmiSSL - Updated SSL libraries that lets the Amiga connect to modern sites

To connect to the internet:

First, ensure that your core is set up with PPP support:
Press F12 to bring up the core menu, then press right once to get the "System"
menu. Make sure the "UART Mode" is set to "PPP".

From the Amiga side, after you have booted to Workbench:

* Start Apps -> Network -> Miami
* Click "Online"
* You are now online (Choose Project -> Iconify in the menu to iconify window)
* Start any of the other apps, e.g. IBrowse to browse the web


Custom scripts:
---------------
If you want to run additional scripts on startup, MegaAGS looks for a file
named Saves:Custom-Startup and runs it, so if you need to run scripts that
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
