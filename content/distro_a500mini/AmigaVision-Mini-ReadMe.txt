# AmigaVision/MegaAGS Setup for The A500 Mini

This is a slimmed down version of the [AmigaVision] setup made specifically for the [A500 Mini] device.

## Quick Start:

* Make sure your USB drive is formatted as FAT32, the A500 Mini does not support exFAT or NTFS.
* Copy the included files in this setup to the root of the drive, the structure should look like this:

```
AmigaVision/
  HDFs/
  Shared/
THEA500/
Start AmigaVision_ol.uae
Start AmigaVision.lha
```

* Plug the USB drive into your A500 Mini, and turn it on.
* Navigate to the "USB Drive" section.
* Select "AmigaVision.lha", press the A button to select it, then press the Menu button to run it.
* Enjoy the best of what the Amiga has to offer!


## Controls:
* Select button brings up the virtual keyboard (and defaults to DEL as the selected key, press this
  to exit the current game and select a new one).
* Start button toggles mouse mode.
* Left and right shoulder buttons are left and right mouse button, respectively.

For full documentation on the rest of the AmigaVision setup, go to the [AmigaVision] web site.

## Notes:

* The A500 Mini is not the most powerful of devices, and does have issues with perfect emulation. This is the same for any setup available for the A500 Mini. For the optimal AmigaVision experience, you unfortunately have to use either MiSTer or original hardware. A fast PC/Mac will also be able to handle it well, but will not do [Dynamic Crop] and [Dynamic Pixel Aspect Ratio] scaling.
* Because of the FAT32 restriction of 4GB, the game selection is a bit more limited than on the real AmigaVision setup. If you have specific games that are missing and you would like to include, file an issue on the [AmigaVision] web site, and we will consider adding it.

[AmigaVision]:https://amiga.vision
[A500 Mini]:https://retrogames.biz/products/thea500-mini/
[Dynamic Crop]:https://amiga.vision/5x
[Dynamic Pixel Aspect Ratio]:https://amiga.vision/sachs
