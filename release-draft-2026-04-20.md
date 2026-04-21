---
title: AmigaVision 2026.04.26 Fast-Follow Update Available
published: false
---

AmigaVision is the ultimate Amiga games *&* demo scene setup for MiSTer *&* Pocket FPGAs, Raspberry Pi + emulators, and real Amiga hardware.

To find out more, visit the [AmigaVision](https://amiga.vision) site.

---

Whenever you ship [the most significant update in your project's history](https://amiga.vision/2026.04.16), you have to plan for a fast-follow release to fix the issues that will inevitably surface — which we did. Thank you to all the Amiga fans out there that identified a ton of hard-to-find issues in a setup with ~5000 game and demo configurations within the first few days! We couldn't do this without you.

This pre-planned fast-follow update for [AmigaVision](https://amiga.vision) covers the fixes and cleanup that landed after the [2026.04.16](https://amiga.vision/2026.04.16) release.

These were the issues we found and fixed in the past few days:

## 🖥️ Platform Updates

* **Proper Raspberry Pi NTSC/PAL native screen refresh rate switching works again** — [Automatic PAL/NTSC switching now works correctly](https://github.com/amigavision/AmigaVision/issues/367). The new RePlayOS releases changed the format of how this was configured, causing 50hz games/demos to run in 60hz, which is obviously unacceptable to us latency/scaling nerds. 😅
* **AutoCrop scaling now available on Raspberry Pi** —  [AutoCrop scaling is now enabled](https://github.com/amigavision/AmigaVision/issues/381) in the Raspberry Pi / RePlayOS setup. Do note that this is *not* the revolutionary 16:9 and 21:9 scaling we do in our emulator setup and MiSTer, but it is a great improvement while we are waiting for a `libretro` core for Amiberry to be added to RePlayOS and RetroArch.
* **Improved emulator timing defaults** — Amiberry-based setups now use [cycle-exact and wait-for-blitter](https://github.com/amigavision/AmigaVision/issues/354) settings. This fixes a large number of demos and games in one fell swoop on emulators. Since we switched to an entirely new emulator as the back-end for AmigaVision, issues such as these were expected — thank you to all our amazing testers for finding these issues within days of release! And if you have other suggestions for settings that will improve the experience, [file tickets in the issue tracker](https://github.com/amigavision/AmigaVision/issues)!
* **MiSTer audio improved** — The MiSTer setup now uses A1200 PWM audio for noticeably clearer sound. Make sure to do a complete clean reinstall to experience this improvement.
* **MiSTer CD32 packaging clarified** — The standalone CD32 setup is no longer bundled into the main MiSTer setup, which avoids confusion now that CD32 has its own dedicated package.

---

* **Kickstart 3.0/3.1 real hardware support added** — Hilariously, we did a lot of testing on original hardware, but all our testers had upgraded Amigas with newer ROMs and 060s etc. — causing this release to not work on unmodified Amiga 1200s with Kickstart 3.0 or 3.1. [This should now work](https://github.com/amigavision/AmigaVision/issues/364), but if you have a 3.0/3.1 Amiga, please help us verify this!
* **MiST support (hopefully) restored** — [MiST FPGA support](https://github.com/amigavision/AmigaVision/issues/373) was not working, but should hopefully be fixed by the `scsi.device` fixes that also make this release of AmigaVision work on Kickstart 3.0 and 3.1 on real hardware. Any MiST users out there, join our testing team! We don't have the hardware, so we rely on your verification. 😄


## 🎮 Game, Demo *&* App Updates

* **Metadata drift corrected** — We did a substantial metadata cleanup pass after the 2026.04.16 release, addressing bugs like [erroneous metadata](https://github.com/amigavision/AmigaVision/issues/355) and games like [Shadow of the Beast not working](https://github.com/amigavision/AmigaVision/issues/357). These should now behave correctly again.
* **King's Quest V Remastered** — The remastered and MT-32 variants were cleaned up so they no longer clutter the main lists with duplicates, and QR-code manual links were added for all of them.
* **Bad Dudes labeling improved** — The launcher now makes it easier to distinguish which *Bad Dudes vs Dragon Ninja* entry is the modern remake.
* **Castlevania CD32 and AGA fixed** — There was a typo in the CD32 launcher and AGA entries for the modern Castlevania version — these have been fixed.
* **Launch path fixes** — [Aventura Espacial & Aventura Original](https://github.com/amigavision/AmigaVision/issues/368) work now.
* **Corrupt archives fixed** — The [Darkage: DeepMeet & Flex: Dead Ahead](https://github.com/amigavision/AmigaVision/issues/375) demos were using bad LhA archives, they now work again.
* **Karateka fixed** — Karateka ST port got corrected artwork and metadata cleanup, resolving [Karateka ST port doesn't load](https://github.com/amigavision/AmigaVision/issues/376).
* **Release years for later ports corrected** — Ports made long after the original era now show more accurate release years, fixing [Years categorised before 1985](https://github.com/amigavision/AmigaVision/issues/377).
* **Beneath a Steel Sky CD32 cleaned up** — The no-voice CD32 variant has been removed since the voiced version is already available.
* **xSysInfo updated to v0.6** — [xSysInfo was updated to v0.6](https://github.com/amigavision/AmigaVision/issues/382).

## 🔧 Launcher Updates

* **Disabling Launcher Music Now Persists** — [disabling launcher music did not persist across reboots](https://github.com/amigavision/AmigaVision/issues/370).
* **Favorites compatibility restored** — [Existing Favorites entries accidentally broke](https://github.com/amigavision/AmigaVision/issues/362) — no data should be lost, the entries just didn't launch, and that should now work again.
* **Launcher timing bug fixed** — A timing issue that could cause graphics corruption in the launcher has been fixed.
* **Launcher navigation improved** — Esc now brings you up one level in the menus, similar to how backspace works. Esc at the top level brings you to Workbench.
* **"Exit to Workbench" entry added** There's now a dedicated entry in the menu to quit the launcher and go to Workbench.
