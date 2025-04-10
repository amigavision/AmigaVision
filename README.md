# AmigaVision

(The latest version of this documentation can also always be found on our web site at [https://amiga.vision/docs])

AmigaVision is a carefully curated collection of game and demo configurations for the [Amiga computer] platform, as well as a minimal [Workbench] setup with useful utilities and apps, wrapped in a user-friendly launcher.

It aims to balance preservation of the historical and current output of the [Amiga games] and [demo scene] as accurately as possible, while still being easy to use for people new to the Amiga computer — making it as easy to use as any game console.

It has many features specifically for use with [MiSTer] and [Analogue Pocket] FPGA devices, but also aims to work with emulators like UAE, handheld emulation devices, and original hardware like the Amiga 1200, Amiga 4000 and Amiga CD32.

## Contents

1. [Features](#features)
2. [Save Files](#save-files)
3. [Upgrading](#upgrading)
4. [Setup for Amiga hardware](#setup-for-amiga-hardware)
5. [Setup for emulators](#setup-for-emulators)
6. [Setup for Pocket](#setup-for-pocket)
7. [Setup for MiSTer](#setup-for-mister)
8. [Optional Setups](#optional-setups)
9. [MiSTer: Gamepad & Joystick Mapping](#mister-gamepad--joystick-mapping)
10. [MiSTer: Video Modes](#mister-video-modes)
11. [MiSTer: CPU Performance Notes](#mister-cpu-performance-notes)
12. [Workbench](#workbench)
13. [CD³² Games Support](#cd-games-support)
14. [Non-working Games](#non-working-games)
15. [Custom Scripts](#custom-scripts)
16. [Bug Reports & Feature Requests](#bug-reports--feature-requests)
17. [Credits](#credits)
18. [Troubleshooting](#troubleshooting)
19. [Frequently Asked Questions](#frequently-asked-questions)

## Features

* Supports original Amiga 1200, 4000 *&* CD32 hardware, MiSTer, MiST and Analogue Pocket FPGA hardware recreations, as well as Amiga emulators.

* Sophisticated and performant Amiga games and demo launcher with screenshots included, can be entirely controlled using gamepads, joysticks or via keyboard. This lets you quickly and easily experience the best of what the system has to offer.

* Close to 2000 hand-tuned, per-game 5× integer scaling with Dynamic Crop settings on MiSTer, ensuring that games and demos make the best use of modern 1080p and 4K 16:9 displays without leaving large parts of the screen blank.

* Carefully curated and well-tested settings for games and demos, no duplication of AGA and ECS versions, with lots of genre and top lists to help you navigate the massive amount of Amiga games available. We take special care to run every game at the correct aspect ratio and CPU speed.

* Games are configured to run in their correct modes, games created in Europe use PAL with 5× Dynamic Crop where appropriate, whereas US-made games run in NTSC for the correct aspect ratio and CPU speed. You can optionally override this in the settings.

* Includes key productions from the legendary Amiga demo scene, including disk magazines sorted chronologically, making it a great companion to explore the demo scene's [UNESCO-nominated] cultural heritage artifacts.

* Hand-tuned scanline and shadow mask settings for MiSTer to get you close to that original CRT look if you are using it on a modern flat panel display. Of course, the setup also works with analog output to real CRT displays.

* Shared file system support for the `MiSTer:` volume, making it trivial to transfer files to and from the Amiga over WiFi or wired networks, or directly using the SD card.

* Internet support is included, you can go online with your Amiga and download apps, games and graphics/music files directly to your setup.

* Minimalist Workbench setup with support for including your own custom set of configurations, games, applications and files using the `Saves:` HD image that will survive upgrades of the main HD image.

* RTG resolution support for running Workbench in modern resolutions like 1920×1080 and in 16:9 aspect ratios on MiSTer.

* Uses PFS as its file system to avoid accidental corruption on write operations, which the standard FFS file system is very prone to.

* Includes a dedicated MiSTer setup to closely mimic a stock Amiga 500 with memory expansion (for use with ADF files only) for maximum compatibility with demo scene productions and any troublesome games that rely on cycle accuracy and exact hardware timings.

* Includes an optional, dedicated Amiga 500HD setup that gives you a representative feel for how it was to use Workbench 1.3 with a hard disk and productivity apps around 1989.

* Includes an optional, dedicated Amiga 600HD setup that gives you a representative feel for how it was to use Workbench 2.x with an Amiga 600 or 3000 and productivity apps around 1991-1992.

* Includes a dedicated Amiga CD32 setup for MiSTer that is compatible with the majority of the released games for it.

## Save Files

Before we start, a quick note on save files:

**IMPORTANT:** For games with save functionality you **MUST** quit the game using the `DEL` key to ensure the save data will be written to "disk", and thus the SD card. You *will* lose your save games if you don't exit the game *after* also saving in-game! 

In the `[Options]` menu of the launcher you can choose between a few alternative quit key options if the `DEL` key doesn't work for you. If set, it will override the preconfigured default Quit key. The active Quit key is displayed on the splash screen shown when a game is loading.

The reason for this is that most games run in a WHDLoad container (think "virtualization"), and cannot write the save data to disk outside the container until you explicitly exit the game.

## Upgrading

When upgrading AmigaVision from a previous release (on any platform), we always recommend following the instructions for doing a clean install and **only** keep your `Saves.hdf` hard drive image, which is where your game saves are stored.

We often make important changes to the configuration files, `MiSTer.ini` and other included files, so the only way to ensure that you can use the new version properly and get the new capabilities (examples from previous releases: 5×PAL Dynamic Scaling, CD32 support on MiSTer, etc.) is to do a clean install of everything, every time. 

Follow the instructions for your platform below.

## Setup for Amiga hardware

AmigaVision supports any AGA-capable Amiga: Amiga 1200, Amiga 4000, and Amiga CD32 — as long as it has a mass storage device like an SD card or CF card connected via an adapter to the IDE bus.

To set up AmigaVision, choose your favorite disk imaging tool — e.g. [Balena Etcher] for Mac, Linux and Windows, [Win32 Disk Imager] for Windows, or whatever tool you prefer for writing to SD/CF cards.

Simply locate the `games/Amiga/AmigaVision.hdf` file, and load that in your disk imaging tool of choice, and write it to the SD/CF card. If the file requester in the disk imaging tool does not allow you to select `.hdf` files, you may need to rename it to have a different extension, e.g. `.img`, `.bin` or similar.

If your HDF image contains every game in the database, you will need a 16GB CF/SD card.

### A note about save files & upgrading on Amiga hardware

Note that save files in games will only be written to disk when you quit the game as described in the [Save Files](#save-files) section.

When installed on a single partition like this, you obviously will overwrite any save files if you upgrade AmigaVision to its newest release. The easiest way is to mount an ADF (or a real floppy!) and copy out the save files before upgrading, and put them back after the new image has been written to your SD/CF card.

Save files are located in `DH0:WHDSaves` — and are usually small enough that all of them fit comfortably on an ADF or a real floppy. So don't let that stop you from upgrading to new and improved versions of AmigaVision, it's really quite easy!

### Joystick and Gamepad support on Amiga hardware

We support single-button Amiga/C64 joysticks, as well as four-button CD32 gamepads, and probably Sega Mega Drive (aka. Sega Genesis) gamepads as well — although we haven't personally tested this.

Many WHDLoad games have been patched to support multiple buttons, so check for those options when starting a game.

## Setup for Emulators

We recommend — and include a setup for — the [FS-UAE] Amiga emulator, which supports Mac, Windows and Linux.

1. Download and install [FS-UAE].
2. Copy the `games/Amiga` directory to your preferred location.
3. Double-click the `AmigaVision.fs-uae` file to run the setup with the preferred settings. You can of course also add a shortcut to this file to your Windows start menu, or as an alias in the Mac's Applications folder.

For any additional configuration or customizations, consult the FS-UAE documentation.

## Setup for Pocket

AmigaVision also works great with the handheld [Analogue Pocket] FPGA device. Do note that the Amiga core on Analogue Pocket does not support mounting/loading disc images for CD³² yet, but the 3000+ games in the library work great.

* Use any of the Pocket updaters to get the OpenFPGA cores, or manually download the latest version of the [Amiga Pocket Core] and put it on your device.
* Copy the files in the AmigaVision directory `games/Amiga` (HDF and ROM files) to the `/Assets/amiga/common` directory on your Pocket SD card.
* Start the Amiga core, enjoy!

### Pocket Controls

* `Select` button brings up the on-screen keyboard, hit `DEL` to quit a game.
* `Start` button toggles mouse emulation mode, left/right triggers are the left/right mouse buttons.
* `A` button selects an entry in the launcher.
* `B` button goes back to the parent category in the launcher.

Many games are updated to support two-button controls, but some require remapping if you prefer button-to-jump instead of up-to-jump (which makes sense on a joystick, but is pretty terrible on a gamepad). Button remapping is done just like in any other Pocket core.

## Setup for MiSTer

Copy the contents of the following directories to the corresponding directories in the top level on MiSTer's file system:

```
_Computer
_Console
config
Filters
games
Presets
Shadow_Masks
```

Paste the following recommended core settings to the bottom of your `MiSTer.ini` file in the root of your MiSTer file system — these settings are further explained in the [Video Modes](#mister-video-modes) section. It's especially important to explicity define resolutions for both PAL and NTSC, and *not* rely on the automatic fallback that MiSTer has available:

```
[Amiga
+Amiga500
+Amiga500HD
+Amiga600HD
+AmigaCD32]
video_mode_ntsc=8 ; These two use the recommended setting of 1080p60 and
video_mode_pal=9  ; 1080p50, adjust if you want a different resolution
vscale_mode=0
vsync_adjust=1 ; You can set this to 2 if your display can handle it
custom_aspect_ratio_1=40:27
bootscreen=0
```

Note that *even if* your 16:9 4K TV *can* handle and scale 1440p, we *still recommend* using 1080p output, since that will do proper integer scaling to 4K and make use of the per-game 5× Zoom and Dynamic Crop modes, to reduce the amount of pixels wasted on black bars along the edges.

### Other monitor sizes

The above default settings assume that you are using it with a 16:9 format 1080p or 4K TV or computer monitor. 

If you are using a 1440p computer monitor (great for scaling ~240p retro gaming output, since 240×6 = 1440) — use these settings for the video modes instead, no matter how many pixels wide it is:

```
video_mode_ntsc=1920,1440,60
video_mode_pal=1920,1440,50
```

Finally, 1920×1200 (16:10) computer monitors are also especially good for scaling ~240p retro gaming output with minimal black borders (since 240×5 = 1200). In that case, use these settings for the video modes:

```
video_mode_ntsc=1920,1200,60
video_mode_pal=1920,1200,50
```

### Using the Amiga Cores

Reboot your MiSTer, you should now have two entries in the `Computer` section, and one in `Console`: 

  * `Amiga` for the main AmigaVision setup — you'll be using this one 99% of the time.
  * `Amiga 500` for a stock Amiga 500 hardware setup with no hard drive to use with ADF floppy disk images for any troublesome demos or games that don't work with the main setup. Some demo ADFs are included and can be mounted as floppy disks in MiSTer's OSD menu, invoked with the `F12` key.
  * `Amiga CD32` for the Amiga CD³² games console — see the instructions for how to load disc images in the dedicated [CD³² section](#cd-games-support)

Launch the `Amiga` entry — and enjoy! Don't forget to check out the other sections of the documentation — especially on save files, controller mappings and video modes — once the basic setup is up and running.

### Potential issues

* If you are using an external hard drive or a network drive, do note that you will have to manually specify the location of the Kickstart file as specified in the [Troubleshooting](#troubleshooting) section.

* If you use `names.txt` to rename cores (or pull it down via the `update_all` script), you may end up with *two* entries that *both* say `Amiga` after this. The entry without a date listed is AmigaVision. To fix this duplication, edit `names.txt` and give the `Minimig` core a different name — e.g. use `Commodore Amiga` for that entry instead, and you can use that for any setups unrelated to AmigaVision, if you so desire.

## Optional Setups

(You can probably skip this section if you were not an Amiga user back in the day or unless you have a special interest in computing history :)

If you used the Amiga back in the day, you may have memories of using an Amiga 500 with a hard disk and Workbench 1.3, or maybe an Amiga 600 or 3000 with Workbench 2.x. We have included dedicated and separate setups for these in the included `Extras` archive.

* Copy the contents of `Amiga 500 HD Setup` and/or `Amiga 600 HD Setup` to their respective directories on the MiSTer or emulators — or, you can of course also use a disk imager to write this to an SD/CF card.
* You will now have separate `Amiga 500HD` and/or `Amiga600HD` launch items in the `Computer` section. These are fully configured to support shared drives, PFS file systems (even on 1.3!), RTC clock, etc.

There are `ReadMe` files that go into more detail about these setups.

These are *not* meant to be used for games or demos, but instead for giving you a basic setup that lets you run productivity apps like you did back in the day. For games and demos, we recommend the `Amiga` (main AmigaVision setup) and `Amiga 500` (for use with ADF files) instead.

## MiSTer: Gamepad & Joystick Mapping

While many games supports two or more buttons, Amiga games were generally designed for one button joysticks. Consequently "up to jump" (or accelerate) control scheme is very common. 

If you are using a gamepad, you might want to use MiSTer's controller mapping to bind the up direction to the D-pad and/or an dedicated jump/accelerate button, typically the `X` button. Here's how:

* First, make sure to have CD32 controller mode enabled (this is the default).
* Enter "Define joystick buttons" mode
* Map directions as usual
* Map the first three buttons (red, blue and yellow) to `A`, `B` and `Y`.
* The fourth button (green) is practically never used, and can be mapped to `Select`, `R2/ZL` or similar — or skipped altogether.
* Go ahead and map right/left triggers and play/pause.
* When asked to if you want to "setup alternative buttons", say Yes!
* Skip all choices except "up", which we recommend mapping to `X`.

While a keyboard and mouse isn't strictly necessary to play most action games, it is definitely recommended for the full Amiga experience, and many games have controls that make use of them.

## MiSTer: Video Modes

We care deeply about preserving the correct aspect ratio for all games. That means going beyond just NTSC and PAL, and ensuring that the Pixel Aspect Ratio (PAR) is also correct. Pixels on the Amiga were close to square (16:15) in PAL resolutions on a CRT, but quite tall on NTSC displays (5:6). Additionally, when we apply a 5×PAL or 6×PAL [Dynamic Crop](https://amiga.vision/5x), 1:1 gives us great results that are near indistinguishable from the original PAR at those sizes, while modernizing the output to fit 16:9 displays.

You no longer have to interact with the MiSTer OSD menu to switch aspect ratios in certain cases like what we informally refer to as "Jim Sachs mode" — NTSC, tall pixels at 5:6 PAR, seen in e.g. Defender of the Crown. Most emulators and captures get this wrong and use 1:1 pixels instead, so we built an implementation that handles all the variants correctly on MiSTer:

* **PAL title, 50Hz:** PAL, 16:15 PAR at 4×, 1:1 PAR at 5× and 6×
* **PAL title, 60Hz:** PAL60, 1:1 PAR at 5×
* **NTSC title, 60Hz:**  NTSC, 1:1 PAR at 5×
* **"World" title, 60Hz:** NTSC, 1:1 PAR at 5×
* **"Sachs NTSC" title, 60Hz:**  NTSC, 5:6 PAR at 5×

All these align to the 1080p/4K 16:9 pixel grid while having the correct Pixel Aspect Ratio, so you will not get any shimmering or non-integer pixels.

On the MiSTer side of things, always, *always* run the AmigaVision setup in the `40:27` aspect ratio that we supply to ensure that this is handled correctly. This is what AmigaVision sets as the default as long as you copy over the supplied config file and have the correct `MiSTer.ini` definition for the core. 

The `Original` aspect ratio supplied by the core should not be used. The `Full Screen` aspect ratio is *only* used for 6×PAL on 16:9 widescreen displays.

Make absolutely sure that you update your `MiSTer.ini` settings for the core [according to the documentation](#setup-for-mister)!

### vsync_adjust setting

The optimal `vsync_adjust` setting in `MiSTer.ini` will depend on your HDMI display. A setting of `2` ensures the lowest possible latency, but it may come at the cost of a short period of no video or audio on video mode changes — something Amiga games and demos do quite often. Setting `vsync_adjust` to `1` introduces a buffer that will smooth over most of these changes, although it will add a frame of latency.

### Dynamic cropping *&* 5× scaling on 1080p/4K displays

A unique feature of the Amiga (Minimig) core on MiSTer is the ability to do viewport cropping. By default the full overscan area will be fed to the HDMI scaler, resulting in huge borders for most content. But fear not! AmigaVision leverages the custom `vadjust` feature of the core to dynamically apply viewport settings on a per-game basis. This depends on MiSTer's "shared folder" functionality, which is enabled in AmigaVision if the "games/Amiga/shared" directory exists. So, make sure you copied all the archive contents as described in the Setup section.

Also note that dynamic cropping *only* applies if you are using 1080p output. Most Amiga games fit on the screen using 5× zoom in this resolution. Any other resolution or analog output is *not* affected by dynamic viewport cropping, as it only makes sense for 1080p/4K 16:9 displays.

With dynamic vadjust enabled, most titles will enjoy a nicely centered viewport at a perfect 5× scale using 1080p output resolution, by cropping the viewport to 216 lines. Games using more than 216 active video lines will instead get a perfect 4× scale by applying a 270 line crop.

## MiSTer: CPU Performance Notes

The D-Cache option in MiSTer's Amiga core is essentially a turbo switch for the CPU, making it perform on par with an accelerated Amiga with a Motorola 68030 CPU at 50MHz in many benchmarks. Unfortunately, running with it enabled introduces lots of subtle glitches in many (mostly older) games and demos, so it's recommended is to leave it `OFF` by default.

The CPU D-Cache option is available in the `OSD` under the `System` menu.

On the other hand, some titles — mostly 3D polygon games and demos — will benefit greatly from the CPU boost D-Cache offers. So it's an option worth experimenting with on a case by case basis. Whenever switching this on or off, we recommend reloading the core to avoid any issues.

## Workbench

From the launcher, you can hit the `ESC` key to exit into Workbench, the AmigaOS graphical desktop environment.

You can explore the world's first multitasking 16-bit computer from 1985 with the addition of a more modern desktop from 1992, AmigaOS 3.

To change from the default 640×200 resolution to something like 1280×720 or 1920×1080 for use with a 16:9 HD display, hold down the right mouse button and select your preferred resolution from the ScreenMode menu. 540p is a nice compromise, a very usable screen resolution that doubles every pixel on a modern 1080p/4K 16:9 display.

## CD³² Games Support

*This section is for MiSTer only. Most emulators have a way to run CD³² games, so consult the documentation there for instructions on how to play CD³² games. The Amiga core on Analogue Pocket does not support mounting/loading disc images yet.*

If you are unfamiliar with the Amiga CD³², it was essentially an Amiga 1200 with a 2× speed CD drive, packaged with gamepads and in a console form factor. It was released in September 1993.

While the CD³² never really got its time to shine because of Commodore’s bankruptcy soon after launch, there are some fun expansions of existing Amiga games with great CD audio and Full Motion Video intros, so some of its ~150 games are worth checking out.

We include a setup in AmigaVision that puts an entry in your `Console` section of MiSTer's core selector. This boots directly into an Amiga setup preconfigured to let you load CD³² games. You will need a mouse, a keyboard or an analog stick set up to act as a mouse to operate this UI.

### Starting a CD³² Game

* Put your CD³² disc images in `games/AmigaCD32` — CHD format is recommended, but BIN/CUE and ISO are also supported.
* Navigate to `Consoles` → `Amiga CD32` and start it.
* You will be presented with a UI, but don't click anything yet.
* Open the MiSTer menu (`F12`), and navigate to the Drives section.
* Navigate to the `Removable/CD` section, and select the CD³² disc image you want to play.
* Dismiss the menu with `ESC`
* Select "Boot"
* Enjoy your game!

Do note that while the majority of CD³² games work (and, even a few CDTV games), this is using a shim combined with MiSTer's CD Audio support in the Amiga core, so not every game will work perfectly — but the majority of them do.

We maintain a compatibility list, including any special settings needed at [amiga.vision/cd32] — make sure to consult the listing for the game you are trying to play if it does not work.

## Non-working Games

About 10 games are currently not working due to CPU or graphics chipset features not yet implemented in MiSTer's Minimig core. Over the past years compatibility has improved a lot, and that trend is likely to continue. The launcher will specify when a game is known not to work in the `Issues` section of a given game.

## Custom Scripts

If you want to run additional scripts on startup, AmigaVision looks for a file named `Saves:custom-startup` on boot and runs it, so if you need to run scripts that will survive upgrades of the main image, this is where to put them.

As an example, here's what you would add to `Saves:custom-startup` if you wanted to make changes to screen resolution, colors, pointers or any other Workbench setting copied from `ENV:Sys/` (which is where Workbench settings are stored temporarily) to `Saves:Custom/Prefs-Env/` before rebooting:

```
copy >NIL: Saves:Custom/Prefs-Env ENV:Sys/
```

This will take the setting you copied to `Saves:Custom/Prefs-Env` and put them in RAM: when booting the image, so you can keep your own settings even when replacing the `AmigaVision.hdf` file with a future version. You can also install new apps/games to Saves: and add `Assign` statements etc to the `Saves:` drive, or do anything else you want to keep permanent after upgrading.

## Bug Reports *&* Feature Requests

While AmigaVision has been tested for many years, the sheer volume of games and demos makes it all but certain that something has been overlooked somewhere. If you find something that doesn't work or seems like it's running with the wrong settings, or something is missing — tell us about it in the issue tracker found under the Development section at [amiga.vision].

## Credits

* [David Lindecrantz] — Creator, original developer
* [Alex Limi] — Developer, current maintainer
* [Per Olofsson] — Creator of [AGS], the launcher software
* [Ben Squibb] — Improvements to AGS to enable hi-res launcher with thumbnail cycling + IFF conversion of hi-res thumbnails
* Simon "[hitm4n]" Quincey — Hi-resolution screenshots for demos
* LamerDeluxe — MT-32 support
* [Frode Solheim] — Creator of [OpenRetro.org], screenshots used with kind permission

## Troubleshooting

### Why doesn't AmigaVision work on my network drive or external drive?

The configuration is likely still looking for your Kickstart file on the path to the SD card. There is currently no way to make this configuration relative in a way that works both on the standard SD card location as well as an SSD or network drive, so you will have to adjust this manually: 

Go to the MiSTer menu → System → ROM, and point it to the location of the file on your SSD or network drive instead. Save this new configuration.

### I get a bunch of errors when starting up!

Unfortunately, there's a lot of variables in what could go wrong, but one useful thing to verify is to make sure the `HDF` file didn't get corrupted on its way to the MiSTer, your Amiga or emulation setup. It's a large file, and there's a lot that can go wrong along the way. The reasons for this happening are legion, but among them:

* You are using FTP to transfer the file, but your FTP client defaults to ASCII instead of binary transfers.
* You are using SMB/Samba, but the implementation of your OS isn't great, and might abort mid-write.
* Your SD card has issues writing the file — very common with cheap or old SD cards.

Let's make sure the image made it over to the target location intact.

The easiest — but a little bit time-consuming — is to compare SHA-1 checksums. MiSTer, Windows, Mac and Linux all have these tools installed by default, but you have to issue some command line instructions to make it work.

1. Do a new, clean transfer of the `HDF` file to MiSTer — ideally not over the network, but if that's your only option, go for it. The reason why you need to do this again is that if the Amiga does any writes to the `HDF` during earlier attempts to launch it, the checksum will be different, and useless for this purpose.
2. Do a clean boot of your MiSTer, and press the `F9` key on a keyboard connected to it. This will let you log in to the terminal. Username is `root`, and password is `1` unless you have changed it in the past.
3. Run the following command, which will take 5-10 minutes to complete: `shasum /media/fat/games/Amiga/AmigaVision.hdf`
4. It will report back a checksum, you will compare this to the checksum on your computer.

Depending on what operating system you are on, you will do one of the following:

* **If you are on macOS:** Open the Terminal, and run the command: `shasum /path/to/AmigaVision.hdf` Compare this to the checksum you got on the MiSTer.

* **If you are on Windows:** Open PowerShell, and run the command: `Get-FileHash C:\path\to\AmigaVision.hdf -Algorithm SHA1` Compare this to the checksum you got on the MiSTer.

* **If you are on Linux:** Open a terminal, and run the command: `shasum /path/to/AmigaVision.hdf` Compare this to the checksum you got on the MiSTer.

If these checksums do not match, something is wrong with either the way you transfer your file, or your SD card. 

If they do match, launching should work without issues, assuming you don't have a bad `HDF` file on your computer.

## Frequently Asked Questions

### Why do you have Scanline and Shadow Mask presets by default?

The Amiga was almost exclusively used with RGB-based CRTs or consumer TVs, and graphics do not look correct without scanlines and shadow masks. We have included a set of Amiga-specific scanline and shadow mask setups to more accurately represent the graphics output of the system that we highly recommend.

Thus, the default setup is configured for this to make sure the most people see the most representative setup. Since configuring this can be intimidating to new users, we chose to have a default that we think best represents the Amiga's original look.

You can of course set your own scanline and shadow mask presets and save those configurations if you don't want to use ours. 

If you are using resolutions lower than 1080p, 1440p or 1536p, we recommend turning them off, but since most users are on 1080p/4K TVs, equally capable monitors, they are on by default.

If you are using analog output to CRTs, these will of course not be used.

### Can I add my own games?

It’s pretty straightforward to add your own games as long as you are a little bit familiar with AmigaOS. Just install the game on the `Saves` HDF drive, and you can add your own launcher entries and thumbnails in the Favorites folder, also located on the `Saves` drive. If you need a template, favorite a random game and open it in a text editor.

### Can I make a setup with only a few games?

The simplest way to do this is to make your own personal collection using the Favorites feature in the launcher. They will be stored on the `Saves` drive, and will survive upgrades.

### Should I worry about Amiga viruses?

In short: No. 

Viruses on the Amiga were quite common, and some retail games even shipped with infected disks in the box. 

Even though we don't control what's being used as inputs to the script that creates the AmigaVision image, pretty much all games and demos run inside WHDL containers, you can think of them as "virtualization for the Amiga". Their job is to insulate the game from the rest of the system, reset CPU vectors, and other system state preservation. So even if a game or demo contains a virus, it cannot stay resident in memory, and will not spread to the rest of the system outside of the sandbox it has been given.

If you want to check the state of a given setup, or whether you have viruses in memory, just run the included VirusZ scanner in the System folder. Again, if you see virus warnings inside of WHDLoad containers, it's nothing to worry about.

We check all files that are under our control for viruses before release.

### I can't get the game started from its title screen! Do I ever need to use "Joystick Swap" on the MiSTer?

Unless you are using the "Arcadia Systems" games (see below), no. On the Commodore 64, games sometimes used Port 1 and sometimes Port 2 for controlling games, necessitating this setting; but since the (Commodore) Amiga shipped with a mouse and it was always plugged into port 1, the main controller is pretty much always connected to port 2. 

The MiSTer core will handle these mappings for you, and joystick port configuration is pretty much never the reason you can't start or control a given game. It's way more likely that you have to hit the space bar, F1, or click a mouse button to get the game started. If you're stuck, look up the controls for a given game in an online manual — which is always a good idea anyway, as there are often additional keyboard or mouse controls needed for a given game for full enjoyment.

### Does AmigaVision work with Kickstart 3.2 or 3.1.4?

While the standard AmigaVision setup expects Kickstart 3.1 (not 3.1.4 or 3.2) — which was the last release from Commodore in 1993 — we have had reports of the setup working if you replace `icon.library` and `workbench.library` with their respective Workbench 3.2 (or 3.1.4) versions. The recommended and tested setup is still Kickstart 3.1.

The files needed can be found on the Workbench Install disk, in the `Libs` drawer.

If you get an error on startup saying "Please insert a volume containing LIBS/workbench.library in any drive", this is likely the reason.

### Are there any plans to support original Amiga 500, Amiga 600, or Amiga 1000 hardware?

Not at the moment, AmigaVision is currently AGA-only and requires at least a 68020 processor. Unless you have added a fair bit of upgrades to these systems, using the AmigaVision setup would be an exercise in frustration, and we also don't have the real hardware to test with when we do a release. 

We welcome contributions, though — so if you're interested in maintaining this part of the AmigaVision setup scripts, let us know!

### What is "Arcadia Systems"?

Arcadia was an unsuccessful venture by Mastertronic to create an Amiga 500-based multi-game arcade system. Most titles released for the system have been dumped and are available via AmigaVision. The games are not great (to put it kindly), but are an interesting curiosity.

Button mapping:

```
P1 Start:    F1
P2 Start:    F2
Left Coin:   F3
Right Coin:  F4
Config:      F5

```

Player 1 uses joystick port 1, while Amiga software universally expect mouse in port 1 and joystick in port 2. If using only one joystick, enable the "Joy Swap" option in the Chipset menu to route the first MiSTer joypad to port 1. It's also worth noting that all Arcadia games make use of a 2-button joystick.

### What are the details of the MiSTer configuration?

If you prefer to configure the main settings manually instead of using the included config files, these are the recommended settings:

```
df0: no disk
df1: no disk
Joystick Swap: OFF
Drives:
  A600/A1200 IDE: On
  Fast-IDE (68020): On
  Primary Master:
    Fixed/HDD
    games/Amiga/AmigaVision.hdf
  Primary Slave:
    Fixed/HDD
    games/Amiga/AmigaVision-Saves.hdf
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
  ROM:
    games/Amiga/AmigaVision.rom
  HRTmon: disabled
Audio & Video:
  TV Standard: NTSC
  Scandoubler FX: Off
  Video area by: Blank
  Aspect ratio: 40:27
  Pixel Clock: 28MHz
  Scaling: Normal
  RTG Upscaling: Normal
  Stereo mix: 50%
  Audio Filter: Auto(LED)
  Model: A500
  Paula Output: PWM

```

[AmigaVision]:https://amiga.vision
[amiga.vision]:https://amiga.vision
[Amiga computer]:https://en.wikipedia.org/wiki/Amiga
[Workbench]:https://en.wikipedia.org/wiki/Workbench_(AmigaOS)
[https://amiga.vision/docs]:https://amiga.vision/docs
[MiSTer]:https://misterfpga.org
[Analogue Pocket]:https://www.analogue.co/pocket
[UNESCO-nominated]:http://demoscene-the-art-of-coding.net
[names.txt]:https://github.com/MiSTer-devel/Main_MiSTer/blob/master/names.txt
[Amiga games]:https://lemonamiga.com
[Demo scene]:https://en.wikipedia.org/wiki/Demoscene
[AGS]:https://github.com/MagerValp/ArcadeGameSelector
[Balena Etcher]:https://www.balena.io/etcher
[Win32 Disk Imager]:https://win32diskimager.org
[FS-UAE]:https://fs-uae.net
[Analogue Pocket]:https://analogue.co/pocket
[Amiga Pocket Core]:https://github.com/Mazamars312/Analogue-Amiga/releases
[amiga.vision/cd32]:https://amiga.vision/cd32

[David Lindecrantz]:https://github.com/Optiroc
[Alex Limi]:https://limi.net
[Per Olofsson]:https://github.com/MagerValp
[Ben Squibb]:https://github.com/stat-mat
[hitm4n]:https://github.com/hittm4n
[Frode Solheim]:https://github.com/FrodeSolheim
[OpenRetro.org]:https://openretro.org

