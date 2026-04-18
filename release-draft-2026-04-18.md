---
title: AmigaVision 2026.04.18 Fast-Follow Update Available
published: false
---

Whenever you ship the most significant update in your project's history, you have to plan for a fast-follow release to fix the issues that will inevitably surface — which we did. Thank you to all our Amiga fans that identified a ton of very obscure issues in a setup with ~5000 game and demo configurations within the first few days! We couldn't do this without you.

This planned fast-follow update for [AmigaVision](https://amiga.vision) covers the fixes and cleanup that landed after the [2026.04.16](https://amiga.vision/2026.04.16) release.

Please see the original [2026.04.16 announcement](https://amiga.vision/2026.04.16) for the details of the massive update of what's new in AmigaVision, these were the issues we found and fixed in the past few days:

## 🔧 Fixes Included in This Update

* **Raspberry Pi NTSC/PAL native screen refresh rate switching works again** — [Automatic PAL/NTSC switching now works correctly again](https://github.com/amigavision/AmigaVision/issues/367). The new RePlayOS releases changed the format of how this was configured, causing 50hz games/demos to run in 60hz, which is obvious unacceptable to us latency/scaling nerds. 😅
* **Improved emulator timing defaults** — Amiberry-based setups now use [cycle-exact and wait-for-blitter](https://github.com/amigavision/AmigaVision/issues/354) settings. This fixes a large number of demos and games in one fell swoop on emulators. Since we switched to an entirely new emulator as the back-end for AmigaVision, this was expected — thank you to all our amazing testers for finding these issues within days of release!
* **Kickstart 3.0/3.1 real hardware support added** — Hilariously, we did a lot of testing on original hardware, but all our testers had upgraded Amigas with newer ROMs and 060s etc. — causing this release to not work on unmodified Amiga 1200s with Kickstart 3.0 or 3.1. [This should now work](https://github.com/amigavision/AmigaVision/issues/364), but if you have a 3.0/3.1 Amiga, please help us verify this!
* **Metadata drift corrected** — A substantial metadata cleanup pass landed after `2026.04.16`, addressing reports of [erroneous metadata](https://github.com/amigavision/AmigaVision/issues/355) and games like [Shadow of the Beast not working](https://github.com/amigavision/AmigaVision/issues/357).
* **Favorites compatibility restored** — [Existing Favorites entries accidentally broke](https://github.com/amigavision/AmigaVision/issues/362) — No data should be lost, the entries just didn't launch, and that should now work again.
* **Launcher timing bug fixed** — A timing issue that could cause graphics corruption in the launcher has been fixed.
* **King's Quest V Remastered** — The remastered and MT-32 variants were cleaned up so they no longer clutter the main lists with duplicates, and QR-code manual links were added for all of them.
* **Bad Dudes labeling improved** — The launcher now makes it easier to distinguish which *Bad Dudes vs Dragon Ninja* entry is the modern remake.
* **Castlevania CD32 and AGA fixed** — There was a typo in the CD32 launcher and AGA entries for the modern Castlevania version — these have been fixed.
* **Launch path fixes** — [Aventura Espacial & Aventura Original](https://github.com/amigavision/AmigaVision/issues/368) work now.
* **Disabling Launcher Music Now Persists** — [disabling launcher music did not persist across reboots](https://github.com/amigavision/AmigaVision/issues/370).
* **MiST support (hopefullly) restored** — [MiST FPGA support](https://github.com/amigavision/AmigaVision/issues/373) was not working, but should hopefully be fixed by the `scsi.device` fixes that also makes it not work on Kickstart 3.0 and 3.1 on real hardware. Any MiST users out there, join our testing team! We don't have the hardware, so we rely on your verification. 😄
* **Corrupt archives fixed** — The [Darkage: DeepMeet & Flex: Dead Ahead](https://github.com/amigavision/AmigaVision/issues/375) demos were using bad LhA archives, they now work again.
