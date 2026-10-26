# Tutankham import

- Source: [LC-Games itch.io release](https://lowcarb.itch.io/tutankham-amiga), downloaded 2026-10-26. Amiga release year: 2026; original Konami arcade game: 1982.
- Original `Tutankham.lha` installed unchanged as `game-notwhdl/Tutankham.lha`. It contains one native Amiga executable, `Tutankham/Tutankham`, with no WHDLoad slave. Direct launcher runs from a persistent `WHDSaves:Tutankham` copy to permit ranking data writes.
- Author lists PAL OCS/ECS/AGA compatibility and 512 KB chip RAM. PAL default selected; no untested overscale/crop preset assigned.
- Controls: joystick/fire, Space for flash bomb, P to pause, Esc for title screen. One player.
- Clean original arcade screenshots from [LaunchBox's arcade gallery](https://gamesdb.launchbox-app.com/games/images/39852-tutankham), visually inspected at native 224×256 resolution, without watermarks or emulator overlays. These depict the arcade source, not captures of the Amiga conversion.
- Title screen `-2`: https://images.launchbox-app.com/5134d789-4590-4621-98c6-d799f20810e1.png
- Gameplay `-3` (default): https://images.launchbox-app.com/cee87cce-53cd-4ea2-bc2b-0e7d6ec7b9c9.png
- Gameplay `-4`: https://images.launchbox-app.com/4aba06c4-9a2f-4955-9643-7210b876128a.png
- Native pixels centered without enlargement or cropping in 404×280 AGA artwork; ECS centered separately in 360×280 with the repository palette converter. Standard artwork centers native pixels in 320×256, then resamples to 320×128.
- Verified archive decoding, Amiga HUNK header, image dimensions/decoding, and ECS source fingerprints. Actual gameplay, exit behavior, timing, and ranking persistence require emulator/hardware validation.

- Launcher palette repair: AGA/standard indices restricted below 240, color zero reserved for black bitmap padding, uncompressed planar encoding verified with the repository checker; ECS counterparts and source fingerprints regenerated.
