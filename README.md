# AmigaVision

**The ultimate Amiga games & demo scene collection for MiSTer & Pocket FPGAs, Raspberry Pi + emulators — and Amiga 1200, 4000 & CD32.**

AmigaVision is a carefully curated collection of game and demo configurations for the Amiga computer platform, as well as a minimal Workbench setup with useful utilities and apps, wrapped in a user-friendly launcher.

It aims to balance preservation of the historical and current output of the Amiga games and demo scene as accurately as possible, while still being easy to use for people new to the Amiga computer — making it as easy to use as any game console.

Full details are on the [AmigaVision](https://amiga.vision) web site.


### Experimental PiStorm SD image

`make pistorm` packages the existing AGA HDF for PiStorm32-lite (A1200).
`make pistorm-ecs` selects the existing ECS HDF for classic
PiStorm (A500/A600/A2000). Both targets prompt for a release date and output
directory, showing the configured defaults; press Enter to accept them.
Noninteractive builds use the defaults without prompting. Build the corresponding
HDF first. Override
`PISTORM_HDF`, `PISTORM_ROM`, or `PISTORM_OUTPUT` when needed; the ROM must suit
the receiving Amiga. The default ROM is `KICKSTART_ROM` from `.env`.

The target downloads checksum-pinned Emu68 1.0.7, WHDLoadWrapper 0.20 and
hdf2emu68 source into `data/cache/pistorm`. It requires the normal Pipenv build
environment, Amiberry, a C compiler and `xz`. Amiberry only installs a small
overlay on a private HDF copy. The original HDF remains untouched. The overlay
preserves the original WHDLoad as `C:WHDLoad.ori`, installs the wrapper's supplied
databases and helpers, disables online wrapper updates, and renames the generic
68040/68060/680x0 libraries so Emu68 can supply its compatibility library.

The `.img.xz` and its `.sha256.txt` and `.md5.txt` checksum files appear in `DISTRO_OUT`.
PiStorm filenames use `AmigaVision-PiStormAGA-<date>.img.xz` or
`AmigaVision-PiStormECS-<date>.img.xz`.
All distro packaging targets write these checksum files beside their finished
release archives. Each checksum refers to the archive itself. The image has
a 64 MiB FAT32 boot partition and an embedded Amiga RDB partition. All boot files and the embedded HDF are checked
before compression. Flash the decompressed **whole image** to a **32 GB or larger
SD card**. This erases the destination card. It includes the supplied Kickstart
ROM, so share it only with testers licensed to use that ROM.

This prototype uses the Amiga's native video output and the internal WHDSaves
fallback. It does not configure RTG or networking. Hardware testers should report
Amiga model, PiStorm model, Pi model, boot/menu behavior, input, game launch/exit,
and whether saves survive a reboot. Try both ordinary WHDLoad titles and native
(non-WHDLoad) games; the wrapper's compatibility settings apply to WHDLoad games.
The prototype is deliberately excluded from `make distros` until tested.
