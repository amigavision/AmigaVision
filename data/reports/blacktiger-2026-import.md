# Black Tiger (2026) import

- Added separately from the 1990 Clipper/U.S. Gold conversion.
- Source: [Str1der's release thread, first post](https://eab.abime.net/showthread.php?t=123925). The post identifies a complete eight-stage Amiga conversion of the Mega Drive port, with an ending and a fixed WHDLoad download.
- Supplied ZIP: `Black Tiger (whdload)(fix).zip`. Repacked losslessly as `game/BlackTiger2026.lha`, with all five files inside `BlackTiger2026/`. Every extracted byte was compared with the supplied ZIP.
- Slave: `BlackTiger2026/BlackTiger.slave`; embedded credits identify amiga-creator, Capcom's 1987 original, and F10 to quit. No installer version is embedded; the database uses the indexer's default v1.0.
- Hardware: OCS, PAL default. The author reports A500 support with 1 MB chip and 1 MB fast RAM; faster performance on A1200. Timing, crop, controls, and playback still need emulator/hardware verification.
- Screenshot source: [LaunchBox original arcade gallery](https://gamesdb.launchbox-app.com/games/images/8269-black-tiger). Native 256×224 PNG captures, visually checked without watermarks or emulator overlays. These depict the original arcade version, not the Amiga conversion.
- Title screen `-2`: https://images.launchbox-app.com/1389ed50-8636-4e8f-852a-e1e9894f2d92.png
- Gameplay `-3` (default): https://images.launchbox-app.com/a427d293-e8c9-4561-826b-c0f93a0e7e96.png
- Gameplay `-4`: https://images.launchbox-app.com/eb861047-c2b8-4602-9f33-67486b8b9b81.png
- Shop `-5`: https://images.launchbox-app.com/762e51ec-cd14-4c74-8743-bb64a617b06e.png
- Sources centered at native 1:1 pixels with black padding: 404×280 AGA, 360×280 ECS, standard prepared at 320×256 before 320×128 half-height resampling. Superseded forum images and slot `-6` removed.
- AGA visible source regions verified pixel-identical to the downloaded PNGs. AGA/standard indices restricted below 240, color zero black, uncompressed planar encoding checked with the repository validator. ECS generated with its separate palette converter; source fingerprints updated.
