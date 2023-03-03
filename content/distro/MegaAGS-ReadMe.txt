# MegaAGS Amiga Setup

MegaAGS creates a carefully curated collection of Amiga games and demos, as well as a minimal Workbench setup with useful utilities and apps, and wraps it all in a user-friendly launcher.

It has many features specifically for use with [MiSTer] FPGA devices, but also aims to work with emulators like UAE and on original AGA-compatible hardware like an Amiga 1200/4000 or CD32, usually with SD/CF card adapters.

Its aim is to balance preserving the historical and current output of the Amiga games and [demo scene] as accurately as possible, while still being easy to use for people new to the Amiga computer.

## Features

* Sophisticated and performant Amiga games and demo launcher with screenshots included, can be entirely controlled using gamepads, joysticks or via keyboard. This lets you quickly and easily experience the best of what the system has to offer.

* Close to 2000 per-game hand-tuned 5× zoom with Dynamic Crop settings, ensuring that games and demos make the best use of modern 1080p 16:9 displays without leaving large parts of the screen blank.

* Carefully curated and well-tested settings for games and demos, no duplication of AGA and ECS versions, with lots of genre and top lists to help you navigate the massive amount of Amiga games available.

* Games are configured to run in their correct modes, games created in Europe use PAL with 5× Dynamic Crop where appropriate, whereas US-made games run in NTSC for the correct aspect ratio and CPU speed. You can optionally override this in the settings.

* Includes key productions from the legendary Amiga demo scene, including disk magazines sorted chronologically, making it a great companion to explore the demo scene's [UNESCO-nominated] cultural heritage artifacts.

* Hand-tuned scanline and shadow mask settings to get you close to that original CRT look if you are using it on a modern flat panel display. Of course, the setup also works with analog output to real CRT displays.

* Shared file system support for the `MiSTer:` volume, making it trivial to transfer files to and from the Amiga over WiFi or wired networks, or directly using the SD card.

* Minimalist Workbench setup with support for including your own custom set of configurations, games, applications and files using the `Saves:` HD image that will survive upgrades of the main HD image.

* RTG resolution support for running Workbench in modern resolutions like 1920×1080 and in 16:9 aspect ratios on MiSTer.

* Uses PFS as its file system to avoid accidental corruption on write operations, which the standard FFS file system is very prone to.

* Includes a dedicated setup to closely mimic a stock Amiga 500 with memory expansion (for use with ADF files only) for maximum compatibility with demo scene productions and any troublesome games that rely on cycle accuracy and exact hardware timings.

* Includes an optional, dedicated Amiga 500HD setup that gives you a representative feel for how it was to use Workbench 1.3 with a hard disk and productivity apps around 1989.

* Includes an optional, dedicated Amiga 600HD setup that gives you a representative feel for how it was to use Workbench 2.x with an Amiga 600 or 3000 and productivity apps around 1991-1992.


## Quick Setup for MiSTer

**Note:** If you are updating from an earlier version -- especially before 2023 -- we *highly* recommend setting aside your `games/Amiga/MegaAGS-Saves.hdf` file and doing this installation from scratch and then adding that file back in, as many things have changed. This is generally always the best approach when upgrading.

* Copy the contents of the following directories to the corresponding directories in the top level on MiSTer's file system:

```  
_Computer
config
Filters
games
Presets
Shadow_Masks

```

* Paste the following recommended core settings to the bottom of your `MiSTer.ini` file in the root of your MiSTer file system -- these settings are further explained in the Video Modes section. It's especially important to explicity define resolutions for both PAL and NTSC, and not rely on the automatic fallback that MiSTer has available:

```
[minimig]
video_mode_ntsc=8
video_mode_pal=9
vsync_adjust=1 ; You can set this to 2 if your display can handle it
custom_aspect_ratio_1=40:27

[Amiga]
video_mode_ntsc=8
video_mode_pal=9
vsync_adjust=1 ; You can set this to 2 if your display can handle it
custom_aspect_ratio_1=40:27

[Amiga500]
video_mode_ntsc=8
video_mode_pal=9
vsync_adjust=1 ; You can set this to 2 if your display can handle it
custom_aspect_ratio_1=40:27

[Amiga500HD]
video_mode_ntsc=8
video_mode_pal=9
vsync_adjust=1 ; You can set this to 2 if your display can handle it
custom_aspect_ratio_1=40:27

[Amiga600HD]
video_mode_ntsc=8
video_mode_pal=9
vsync_adjust=1 ; You can set this to 2 if your display can handle it
custom_aspect_ratio_1=40:27

```

* Reboot your MiSTer, you should now have two entries in the `Computer` section: 
  * `Amiga` for the main MegaAGS setup -- you'll be using this one 99% of the time.
  * `Amiga 500` for a stock Amiga 500 hardware setup with no hard drive to use with ADF floppy disk images for any troublesome demos or games that don't work with the main setup. Some demo ADFs are included and can be mounted as floppy disks in MiSTer's OSD menu, invoked with the `F12` key.

* Launch the `Amiga` entry and enjoy! Don't forget to check out the sections below -- especially on save files, controller mappings and video modes once the basic setup is up and running.

## Optional Setups for MiSTer

(You can probably skip this section if you were not an Amiga user back in the day or unless you have a special interest in computing history :)

If you used the Amiga back in the day, you may have memories of using an Amiga 500 with a hard disk and Workbench 1.3, or maybe an Amiga 600 or 3000 with Workbench 2.x. We have included dedicated and separate setups for these in the `Extras` folder.

* Copy the contents of `Amiga 500 HD Setup` and/or `Amiga 600 HD Setup` to their respective directories on the MiSTer
* You will now have separate `Amiga 500HD` and/or `Amiga600HD` launch items in the `Computer` section. These are fully configured to support shared drives, PFS file systems (even on 1.3!), RTC clock, etc.

There are `ReadMe` files that go into more detail about these setups.

These are *not* meant to be used for games or demos, but instead for giving you a basic setup that lets you run productivity apps like you did back in the day. For games and demos, we recommend the `Amiga` (main MegaAGS setup) and `Amiga 500` (for use with ADF files) instead.

## Gamepad & Joystick Mapping for MiSTer

While many games supports two or more buttons, Amiga games were generally designed for one button joysticks. Consequently "up to jump" (or accelerate) control scheme is very common. If you are using a gamepad, you might want to use MiSTer's controller mapping to bind the up direction to the D-pad and/or an dedicated jump/accelerate button, typically the `X` button. Here's how:

* First, make sure to have CD32 controller mode enabled (this is the default).
* Enter "Define joystick buttons" mode
* Map directions as usual
* Map the first three buttons (red, blue and yellow) to `A`, `B` and `Y`.
* The fourth button (green) is practically never used, and can be mapped to `Select`, `R2/ZL` or similar -- or skipped altogether.
* Go ahead and map right/left triggers and play/pause.
* When asked to if you want to "setup alternative buttons", say Yes!
* Skip all choices except "up", which we recommend mapping to `X`.

While a keyboard and mouse isn't strictly necessary to play most action games, it is definitely recommended for the full Amiga experience, and many games have controls that make use of them.


## Save Files

**IMPORTANT:** For games with save functionality you **MUST** quit the game using the `DEL` key for the save data to be written to "disk", and thus the SD card. You *will* lose your save games if you don't exit the game *after* also saving in-game! 

In the `[Options]` menu of the launcher you can choose between a few alternative quit key options if the `DEL` key doesn't work for you. If set, it will override the preconfigured default Quit key. The active Quit key is displayed on the splash screen shown when a game is loading.

## Video Modes

The optimal `vsync_adjust` setting in `MiSTer.ini` will depend on your HDMI display. A setting of `2` ensures the lowest possible latency, but it may come at the cost of a short period of no video or audio on video mode changes -- something Amiga games and demos do quite often. Setting `vsync_adjust` to `1` introduces a buffer that will smooth over most of these changes, although it will add a frame of latency.

A unique feature of the Amiga (Minimig) core on MiSTer is the ability to do viewport cropping. By default the full overscan area will be fed to the HDMI scaler, resulting in huge borders for most content. But fear not! MegaAGS leverages the custom `vadjust` feature of the core to dynamically apply viewport settings on a per-game basis. This depends on MiSTer's "shared folder" functionality, which is enabled in MegaAGS if the "games/Amiga/shared" directory exists. So, make sure you copied all the archive contents as described in the Setup section.

Also note that the dynamic cropping *only* applies if you are using 1080p output. Most Amiga games fit on the screen using 5× zoom in this resolution. Any other resolution or analog output is *not* affected by dynamic viewport cropping, as it only makes sense for 1080p/4K 16:9 displays.

With dynamic vadjust enabled, most titles will enjoy a nicely centered viewport at a perfect 5× scale using 1080p output resolution, by cropping the viewport to 216 lines. Games using more than 216 active video lines will instead get a perfect 4× scale by applying a 270 line crop.

Next, let's talk about Pixel Aspect Ratio (PAR). Most Amiga graphics were drawn targeting a roughly square pixel display, if considering standard low resolution mode in PAL. However, some American games were drawn using the 320x200px NTSC mode stretched to cover a 4:3 display, yielding distinctly narrower pixels. Using MiSTer's capability for setting up custom aspect ratios, it is possible to quickly toggle between these PARs via OSD -> Audio & Video -> Aspect ratio. When you add the `custom_aspect_ratio` override to `MiSTer.ini` as specified in the setup section, you will be able to toggle between `Original` and `40:27` settings (as well as the fully useless `Full screen` setting, please don't use this).

`Original` will yield square pixels for full-height PAL titles, and the sometimes correct narrow pixels for NTSC games. `40:27` will result in square pixels for PAL (5×) titles and NTSC/PAL60 titles. As guidance, use these settings depending on what video mode the launcher UI denotes in the info section for the game for best results:

```
4×PAL      Original
5×PAL      40:27
5×PAL60    40:27
5×NTSC     Original (or occasionally 40:27, depending on title)

```

Generally, if you leave it on the default setting (`40:27`), most popular Amiga games will appear in the correct aspect ratio. Exceptions are US-produced games like e.g. Defender of the Crown, which were made using the narrower NTSC resolutions.

Again, make sure to add the Minimig core overrides in MiSTer.ini as specified in the setup section to enjoy the best HDMI output possible, and make sure you have set MiSTer to output in 1080p resolution.

## CPU Performance Notes

The D-Cache option is essentially a turbo switch for the CPU, making it perform on par with an accelerated Amiga with a Motorola 68030 CPU at 50MHz in many benchmarks. Unfortunately, running with it enabled introduces lots of subtle glitches in many (mostly older) games and demos, so it's recommended is to leave it *OFF* by default.

The CPU D-Cache option is available in the `OSD` under the `System` menu.

On the other hand, some titles -- mostly 3D polygon games and demos -- will benefit greatly from the CPU boost D-Cache offers. So it's an option worth experimenting with on a case by case basis.

Note that the glitches introduced with D-Cache on can sometimes clear up by turning it off while the Amiga core is running. Other times they seem to stick until reboot. The latter behavior is the case with, for example, Turrican II and Grand Monster Slam (and many less significant titles). Whenever making changes to the System settings in the OSD, we recommend re-loading the core.


## Manual Configuration

(You can skip this section if you followed the earlier instructions)

For reference, if you prefer to configure the main settings manually instead of using the included config files, these are the recommended settings used:

```
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
  Joystick: CD32
  ROM: games/Amiga/MegaAGS-Kickstart.rom (or whatever your 3.1.x ROM is called)
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

```

## Workbench

From the launcher, you can hit the `ESC` key to exit into Workbench, the AmigaOS graphical desktop environment.

You can explore the world's first multitasking 16-bit computer from 1985 with the addition of a more modern desktop from 1992, AmigaOS 3.

To change from the default 640×200 resolution to something like 1280×720 or 1920×1080 for use with a 16:9 HD display, hold down the right mouse button and select your preferred resolution from the ScreenMode menu. 540p is a nice compromise, a very usable screen resolution that doubles every pixel on a modern 1080p/4K 16:9 display.


## Non-working Games

About 10 games are currently not working due to CPU or graphics chipset features not yet implemented in MiSTer's Minimig core. Over the past years compatibility has improved a lot, and that trend is likely to continue. A few titles do not work, or are very glitchy, due to other inaccuracies. This will also likely improve over time. The launcher will specify when a game is known not to work in the `Notes` section of a given game.


## Custom Scripts

If you want to run additional scripts on startup, MegaAGS looks for a file named `Saves:custom-startup` on boot and runs it, so if you need to run scripts that will survive upgrades of the main image, this is where to put them.

As an example, here's what you would add to `Saves:custom-startup` if you wanted to make changes to screen resolution, colors, pointers or any other Workbench setting copied from `ENV:Sys/` (which is where Workbench settings are stored temporarily) to `Saves:Custom/Prefs-Env/` before rebooting:

```
copy >NIL: Saves:Custom/Prefs-Env ENV:Sys/

```

This will take the setting you copied to `Saves:Custom/Prefs-Env` and put them in RAM: when booting the image, so you can keep your own settings even when replacing the `MegaAGS.hdf` file with a future version. You can also install new apps/games to Saves: and add `Assign` statements etc to the `Saves:` drive, or do anything else you want to keep permanent after upgrading.

## Found Bugs? Want to Request Features?

While MegaAGS has been tested for many years, the sheer volume of games and demos makes it all but certain that something has been overlooked somewhere. If you find something that doesn't work or seems like it's running with the wrong settings, or something is missing -- tell us about it in the issue tracker at https://amiga.vision.

## Frequently Asked Questions

### What does the `Minimig` core do now that I have an `Amiga` setup?

We use the `Amiga` and `Amiga 500` MGL files to launch the Minimig core with  dedicated configurations. The Minimig entry isn't used directly anymore, but it will launch (and share files with) the main `Amiga` setup. Just ignore the Minimig entry or rename it using your own [names.txt] if you want.

This also lets us have the `Amiga 500HD` and `Amiga 600HD` setups with separate hard disk images, shared files, etc.

We find this to be a more usable and cleaner setup, instead of using the core configuration selectors that cannot be named, and lets you have e.g. the Amiga 500 setup easily available on the top level for use with demos and games that do not work on a "modern" Amiga HD-based setup.

### Why do you have Scanline and Shadow Mask presets by default?

The Amiga was almost exclusively used with RGB-based CRTs or consumer TVs, and graphics do not look correct without scanlines and shadow masks. We have included a set of Amiga-specific scanline and shadow mask setups for use with MiSTer to more accurately represent the graphics output of the system that we highly recommend.

Thus, the default setup is configured for this to make sure the most people see the most representative setup. Since configuring this can be intimidating to new users, we chose to have a default that we think best represents the Amiga's original look.

You can of course set your own scanline and shadow mask presets in MiSTer's menus and save those configurations if you don't want to use ours. 

If you are using resolutions lower than 1080p, 1440p or 1536p, we recommend turning them off, but since most MiSTer users are on 1080p/4K TVs (or analog CRTs), they are on by default.

### I can't get the game started from its title screen! Do I ever need to use "Joystick Swap"?

Unless you are using the "Arcadia Systems" games (see below), no. On the Commodore 64, games sometimes used Port 1 and sometimes Port 2 for controlling games, necessitating this setting; but since the (Commodore) Amiga shipped with a mouse and it was always plugged into port 1, the main controller is pretty much always connected to port 2. 

The MiSTer core will handle these mappings for you, and joystick port configuration is pretty much never the reason you can't start or control a given game. It's way more likely that you have to hit the space bar, F1, or click a mouse button to get the game started. If you're stuck, look up the controls for a given game in an online manual -- which is always a good idea anyway, as there are often additional keyboard or mouse controls needed for a given game for full enjoyment.

### What's "Arcadia Systems"?

Arcadia was an unsuccessful venture by Mastertronic to create an Amiga 500 based multi-game arcade system. Most titles released for the system have been dumped and are available on the MegaAGS image. The games are not great (to put it kindly), but are an interesting curiosity.

Button mapping:

```
P1 Start:    F1
P2 Start:    F2
Left Coin:   F3
Right Coin:  F4
Config:      F5

```

Player 1 uses joystick port 1, while Amiga software universally expect mouse in port 1 and joystick in port 2. If using only one joystick, enable the "Joy Swap" option in the Chipset menu to route the first MiSTer joypad to port 1. It's also worth noting that all Arcadia games make use of a 2-button joystick.


[MiSTer]:https://misterfpga.org
[UNESCO-nominated]:http://demoscene-the-art-of-coding.net
[names.txt]:https://github.com/MiSTer-devel/Main_MiSTer/blob/master/names.txt
[Demo scene]:https://en.wikipedia.org/wiki/Demoscene
