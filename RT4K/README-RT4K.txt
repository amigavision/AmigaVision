# RetroTink 4K profiles for MiSTer using DV1

If you are using the RetroTink 4K scaler, we have included some pre-configured profiles to get you started. These are optimized for use with MiSTer, but can also be used with emulation software and real hardware, although they won't auto-switch to the correct profile like they do with MiSTer's DV1 signalling — you will have to manually load them in the RT4K Profile menu.

## Installation

* Copy the contents of the `RT4K` directory to the root of the SD card you are using in your RetroTink 4K.

  * Note that we have included profiles for most of the mainstream computer and console cores on the MiSTer, but if you already have your own settings for these, 
just say no if it asks you to overwrite those files.

* On your MiSTer: Make sure you have enabled `direct_video = 1` in your `MiSTer.ini` 

  * If you want to avoid weird scaling on the main MiSTer menu, you can except the menu core from being scaled:

```
[menu]
direct_video=0
```

* On the RetroTink 4K: Make sure you have enabled `Profiles` → `Auto Load DV1: On`


## Usage

If you are using a MiSTer, the correct profile will automatically be selected for a given console, as long as you turned it on during the installation steps.

If you are using any other device, navigate to the Profiles menu, and load them manually.

If the image from a given game does not go all the way to the edges, hit the `AUX1` button on the controller. Especially on the Amiga, the offsets vary wildly, so one default setting can't serve every game. 

We are looking into whether we can signal this directly from the Amiga core on a per-game basis, like we currently do with the 5×PAL scaling we do on MiSTer, but this is not implemented yet — so, use that AUX1 button once you are inside the game to make use of all your lovely 4K pixels!
