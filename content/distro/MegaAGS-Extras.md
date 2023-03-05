# MegaAGS Extras 

In addition to the main setup, we include some additional images and convenience functions that may be of interest to the Amiga connoisseur.

## Amiga 500HD Setup

This hard disk setup aims to recreate an Amiga 500 with Kickstart/Workbench 1.3, the setup of an Amiga 500/1000/2000 power user from around 1989. Think Amiga 500 with a GVP HD8+ or A590 attached, supplying a hard disk and memory expansion.

This is implemented as a separate MGL file and directory setup for MiSTer, letting you have a separate setup that doesn't affect the main MegaAGS game/demo image.

It aims to recreate the setups that were common before the Amiga 600/1200 were released with hard disk support and a more modern OS.

Common applications like Directory Opus, ProTracker, music players and graphics/audio problems are already included in the Apps menu in Workbench, giving you a great starting point for your own custom setup.

In addition, the image includes:

* MiSTer `shared/` directory support to facilitate easy sharing of files between MiSTer's file system and the Amiga file system
* Custom patch for Kickstart 1.3 for HD support
* PFS file system that protects against accidental file system corruption if restarted during a write operation
* Launch menu in Workbench for common applications

We default this setup to NTSC for compatibility reasons, but you can easily change it to PAL in *MiSTer's Audio & Video settings* menu for the Amiga core if you prefer that.

We recommend using the separate, dedicated Amiga 500 setup for ADF format game disks and demo disks, this setup is for people interested in running a Workbench setup.

**Quick setup:**

* Copy MGL file to /_Computer
* Copy config file to /config
* Copy the A500HD directory and its contents to /games
* Cold reboot the MiSTer
* You now have a dedicated entry for "Amiga 500HD" in the MiSTer menu

## Amiga 600HD Setup

This hard disk setup aims to recreate an Amiga 600HD (or an Amiga 500 Plus or Amiga 3000) with Kickstart 2.0 and Workbench 2.1. This would be the setup of an Amiga 500+/600/3000 user with a hard drive, memory expansion (and possibly an accelerator card) from around 1991-1992, common before the Amiga 1200/4000 computers that included the newer AGA graphics chipset and AmigaOS 3.0/3.1.

This is implemented as a separate MGL file and directory setup for MiSTer, letting you have a separate setup that doesn't affect the main MegaAGS game/demo image.

In addition, the image includes:

* MiSTer `shared/` directory support to facilitate easy sharing of files between MiSTer's file system and the Amiga file system
* Custom patch for Kickstart 1.3 for HD support
* PFS file system that protects against accidental file system corruption if restarted during a write operation
* Launch menu in Workbench for common applications

We default this setup to NTSC for compatibility reasons, but you can easily change it to PAL in the *Workbench ScreenMode Preferences* if you prefer that.

Common applications like Directory Opus, ProTracker, music players and graphics/audio problems are already included in the Apps menu in Workbench, giving you a great starting point for your own custom setup.

The default setup enables the faster CPU by default since this setup isn't really meant to be used for games that require cycle accurate CPU compatibility. You can switch the CPU to 68000 in the MiSTer core menu for the Amiga core if you want the orignal A500+/A600 speed instead of something that resembles an Amiga 3000.

We recommend using the separate, dedicated Amiga 500 setup for ADF format game disks and demo disks, this setup is for people interested in running a Workbench setup.

**Quick setup:**

* Copy MGL file to /_Computer
* Copy config file to /config
* Copy the A600HD directory and its contents to /games
* Cold reboot the MiSTer
* You now have a dedicated entry for "Amiga 600HD" in the MiSTer menu

# Empty PFS Save Images

We have included several larger sizes of pre-formatted PFS `MegaAGS-Saves.hdf` files, should you want to create your own custom setup based on MegaAGS without having to re-do your customizations every time. The reason it's important to use PFS instead of creating your own FFS-based Amiga HD images is that PFS protects against accidental corruption of the HD if you reset the computer during a write operation. It's also faster than an FFS image, and the rest of the MegaAGS setup uses PFS everywhere for that same reason.

The main MegaAGS image will check for `Saves:custom-startup` and execute that when found. This lets you e.g. copy any custom settings to `ENV:` as part of the startup, so you can have your own Workbench, Directory Opus and custom application installs on a separate hard drive that survives upgrades to the main MegaAGS image.

Note that these are contained in a 7zip archive file to make sure they don't take any additional space in the main archive. Only unpack these if you intend to use them, as they will take up several gigabytes of storage if you do.