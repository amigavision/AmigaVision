# AmigaVision/MegaAGS Setup for Analogue Pocket

This is a slimmed down version of the [AmigaVision] setup made specifically for the [Analogue Pocket] FPGA handheld.

## Quick Start:

* Download the [latest version] of the Amiga core for the Analogue Pocket and put it on your device.
* Copy the included files in this setup to the `/Assets/amiga/common` directory on your Pocket SD card.
* Start the Amiga core.

## If upgrading:

Ensure that the core settings (when you press the Analogue button) are set to:

* Screen X Position: 154
* Screen Y Position: 40

These values will be correct if this is your first installation of the core, but 
as these aren't overridden when you upgrade, you need to manually ensure you have 
the correct offset for this version of the core.

## Controls:
* Select button brings up the virtual keyboard (and defaults to DEL as the selected key, press this
  to exit the current game and select a new one).
* Start button toggles mouse mode.
* Left and right shoulder buttons are left and right mouse button, respectively.

For full documentation on the rest of the AmigaVision setup, go to the [website].

## Troubleshooting + Notes:

* This is a computer core, and will take a while to do the initial load compared to the console cores.
  15-30 seconds before the game launcher is visible is not unexpected, be patient.
  Subsequent game launches are much quicker.
* If you had an old build of the Amiga core for Pocket, we recommend resetting to default settings to
  ensure that you are using the optimal settings.

 [AmigaVision]:https://amiga.vision
 [Analogue Pocket]:https://analogue.co/pocket
 [website]:https://amiga.vision/docs
 [latest version]:https://github.com/Mazamars312/Analogue-Amiga/releases
