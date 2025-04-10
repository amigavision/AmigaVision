# AmigaVision Setup for A500 Mini (Beta)

This is a slimmed down version of the [AmigaVision] setup made specifically for the [A500 Mini] device.


## What this is:

* A fast, beautiful launcher with thumbnail previews that can be operated by anyone with a game pad, joystick or keyboard, with built-in favorites support.
* A highly curated collection of games and demo scene productions that covers the best of the Amiga, without drowning you in listings.
* A fast, streamlined Amiga setup that gets you to your games as quickly as possible.
* A familiar setup using the same approach as the highly-regarded AmigaVision MiSTer FPGA and Analogue Pocket FPGA setups.


## What this is not:

* An Amiga setup with a pimped-out "Amiga of the future" Workbench with RTG, 16M colors, MUI, tons of "productivity" apps. 
* A launcher for every single Amiga game ever released.

Plenty of those setups exist out there, but this is not that. :)


## Quick Start:

* Make sure your USB drive is formatted as FAT32, the A500 Mini does not support exFAT or NTFS.
* Copy the included files in this setup to the root of the drive, the structure should look like this:

```
Shared/
THEA500/
  whdboot/
AmigaVision-Mini.hdf
AmigaVision-Saves.hdf
Start AmigaVision_ol.uae
Start AmigaVision.lha
```

* Plug the USB drive into your A500 Mini, and turn it on.
* Navigate to the "USB Drive" section.
* Select "Start AmigaVision.lha", press the `A` button to select it, then press the Menu button to run it.
* Enjoy the best of what the Amiga has to offer!


## A500 Mini Controls:

* `Menu` button toggles the on-screen keyboard. 
* While in a game, press `DEL` to exit the current game and select a new one. (TODO: Change to F10?)
* To exit out of the AmigaVision setup to the A500 Mini menu, press the power button briefly — the Home button does not work.

For full documentation on the rest of the AmigaVision setup, go to the [AmigaVision] web site.


## Notes:

* The A500 Mini is not the most powerful of devices, and does have issues with perfect emulation. This will be the same for any setup made for the A500 Mini, and if you are looking for accurate Amiga performance, there are versions of the AmigaVision setup for real hardware, MiSTer and Analogue Pocket FPGAs, as well as PC & Mac emulators.
* Because of the FAT32 restriction of 4GB, the game selection is a bit more limited than on the real AmigaVision setup. If you have specific games that are missing and you would like to include, file an issue on the [AmigaVision] web site, and we will consider adding it.
* Tested on the original Mini firmware (1.0.x), and also the latest available firmware at this time (v1.1.1). We recommend the latest firmware.

## Still in Beta:

* There is currently no support for [Dynamic Crop] or [Dynamic Pixel Aspect] Ratio on emulators, nor on the A500 Mini.
* NTSC games are still not scaling the way we'd like, but we are working on improving the situation -- running 60hz games under 50hz displays will have some trade-offs.


[AmigaVision]:https://amiga.vision
[A500 Mini]:https://retrogames.biz/products/thea500-mini/
[Dynamic Crop]:https://amiga.vision/5x
[Dynamic Pixel Aspect]:https://amiga.vision/sachs
