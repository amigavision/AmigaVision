# Requested additions, October 2026

The archives live in the configured `$AVSCONTENT/titles` library. Launch scripts,
SHA-256 manifests and launcher artwork are tracked in this repository.

## Sources

- [#472](https://github.com/amigavision/AmigaVision/issues/472): [AmiGoonies AGA v0.4](https://marlox.itch.io/the-amigoonies)
  - Source SHA-256: `d55852ca15d01ba8255eba31b299927166f7272bba268f54c92ce8460ac411c2`
- [#472](https://github.com/amigavision/AmigaVision/issues/472): [Aonic demo 1](https://reassembler68k.itch.io/aonic)
  - Source SHA-256: `1509ce2be1e7a4f7825027a1b709e2520d043f3e6d89cbc9f2222b4ff287e4c5`
- [#457](https://github.com/amigavision/AmigaVision/issues/457): [Oids HD](http://meynaf.free.fr/pr/oids.lzx)
  - Source SHA-256: `891c6eb0cbd0538a15c01fb347faccea1cac71c24c4fc895b25a8d0622113e75`
- [#456](https://github.com/amigavision/AmigaVision/issues/456): [Worms DC 30th Anniversary Expansion Pack](https://worm.net/zip/wdc30.zip)
  - Source SHA-256: `676669130c5df66338aa6e0cd15b601231cb9a0d69221dd67c8dc85a16d3b0fd`
- [#453](https://github.com/amigavision/AmigaVision/issues/453): [Haujobb: Megademo 2000](https://archive.scene.org/pub/parties/2000/theparty00/amiga/demo/hjb-md2k.lha)
  - Source SHA-256: `4a77ebe59041894eeed1831fa1308dfd30ef6172eb2ab559f41b2a2dd8e5097d`

## Packaging

- `game-notwhdl/AmiGooniesAGA.lha`: rename the Workbench archive's `amigoonies` drawer to `AmiGooniesAGA`; run `amigoonies` from it. This is the AGA playable preview, not a completed game.
- `game-notwhdl/AonicAGA.lha`: extract the ADF with `xdftool`, place `aonic`, `data` and `readme.txt` in `AonicAGA`, and omit the floppy startup sequence. The supplied readme explicitly supports copying the folder structure to a hard drive.
- `game-notwhdl/Oids.lha`: unpack the original LZX archive and rename the `oids` drawer to `Oids`; launch `oids` directly.
- `demo-notwhdl/Haujobb-Megademo2000-060.lha`: rename `hjb-md2k` to `Haujobb-Megademo2000-060`; run `HJB-MD2K.exe`. The production text specifies A4000, 68060/50, 2 MB Chip and 32 MB Fast RAM.
- `game/WormsDirectorsCut30thAnniversary_v1.3_AGA_12MB.lha`: copy the existing `WormsDirectorsCut_v1.3_AGA_12MB_0605.lha` install, rename its drawer to `WormsDC30AGA12MB`, and unpack every expansion file into its `data` directory. Keep the original `WormsDCAGA12MB.Slave` and `CUSTOM1=1`. The expansion is a separate menu entry and archive.

Repack each drawer with native LhA. Generate manifests with `avs_index.make_manifest`. Copy each non-WHDLoad `.run` beside its archive in the external library, matching the tracked copy.

## Existing request

[#452](https://github.com/amigavision/AmigaVision/issues/452) is already installed as `demo--bigdemo--bigdemo` with its WHDLoad slave and artwork. Its included `BIG_Demo_ReadMe` identifies the Amiga conversion as 1997; the database year has been corrected from the Atari original's 1988.

## Artwork

AmiGoonies and Aonic screenshots come from their author pages above; Megademo 2000 uses the [Pouet screenshot](https://www.pouet.net/prod.php?which=2367). Oids screenshots come from [Amiga France](https://www.amigafrance.com/forums/topic/oids/). The expanded Worms entry reuses the existing Director's Cut artwork. Screenshots are fitted on the 640 x 512 conversion canvas before creating the medium, high-resolution and ECS IFF assets.

## Verification

Archive manifests, launch targets, CSV shape and unique IDs were checked. The native indexer rediscovers all five new IDs. Every unaffected base Worms file and every expansion file was compared byte-for-byte with its source. These are packaging checks; the new launches still need an emulator or hardware play-test before the issues are closed.

## Second batch

The following requests are packaged as additional entries:

| Issue | Title | Source |
| --- | --- | --- |
| [#268](https://github.com/amigavision/AmigaVision/issues/268) | Citadel: Remonstered | Locally staged `Citadel_v1.4_RemonsteredEdition.lha`; complete WHDLoad install |
| [#410](https://github.com/amigavision/AmigaVision/issues/410) | Connect v1.6 | [Author's ADF](https://logicalbyte.itch.io/connect), including generic Kickstart 1.3 slave |
| [#322](https://github.com/amigavision/AmigaVision/issues/322) | BattleDuel v1.7.105 | [Complete freeware distribution](https://aminet.net/package/game/2play/BattleDuel) |
| [#218](https://github.com/amigavision/AmigaVision/issues/218) | SuperDodge | [Aminet](https://aminet.net/package/game/2play/SuperDodge) |
| [#285](https://github.com/amigavision/AmigaVision/issues/285) | NEONnoir v1.2.2 | [Author-supplied WHDLoad MULTI3 package](https://steamknight.itch.io/neonnoir) |
| [#307](https://github.com/amigavision/AmigaVision/issues/307) | Dr. Dangerous | [Author's free version, hotfix 2](https://hoogames2017.itch.io/dr-dangerous) |
| [#316](https://github.com/amigavision/AmigaVision/issues/316) | +=+ | [Spreadpoint release archive](https://2go.ch/dist/spreadpoint-plusequalsplus.zip) |
| [#405](https://github.com/amigavision/AmigaVision/issues/405) | Metropolice | [Ghostown/RNO release archive](https://ftp.untergrund.net/users/breakpoint/2010/amiga_demo/metropolice.lha) |
| [#391](https://github.com/amigavision/AmigaVision/issues/391) | Caribbean Disaster / Hoodlum | [Janeway](https://janeway.exotica.org.uk/release.php?id=14775) |
| [#391](https://github.com/amigavision/AmigaVision/issues/391) | Nitro / Horizon | [Janeway](https://janeway.exotica.org.uk/release.php?id=6559), disk 1 cracktro |
| [#391](https://github.com/amigavision/AmigaVision/issues/391) | Flashback / Interpol | [Janeway](https://janeway.exotica.org.uk/release.php?id=14573) |
| [#391](https://github.com/amigavision/AmigaVision/issues/391) | History Line / TRSI | [Janeway](https://janeway.exotica.org.uk/release.php?id=9050), German cracktro |
| [#249](https://github.com/amigavision/AmigaVision/issues/249) | Formula One Grand Prix: 16 FPS | [2018 competition package](https://www.lemonamiga.com/forum/viewtopic.php?t=14953), including WHDLoad slave |

Rift (#405) and Ministry's Project-X SE cracktro (#391) already have database entries and local archives. World Circuit (#249) is also installed; its redundant/preferred flags have been removed so it is independently selectable.

### Installation details

- Citadel and NEONnoir retain their supplied WHDLoad packages unchanged. Citadel saves into `Disk.4` and requires the in-game F10 exit to flush saves, as noted in its launcher metadata.
- Connect uses the bundled slave with `DATA=data CUSTOM=connect.exe NOMMU`, preserving the v1.6 executable and assets from the ADF. The explicit program name avoids relying on the old icon's `Custom=connect` setting. `NOMMU` follows the installer's 68060 requirement.
- BattleDuel retains the complete original archive, including documentation and all graphics variants. Its `BDSAVE:` assign points to `WHDSaves:BattleDuel`; the launcher seeds `Settings/Default.set` only on first run.
- SuperDodge is wrapped in a `SuperDodge` drawer and launched directly. It uses the left mouse button for player 1 and joystick fire for player 2.
- Dr. Dangerous retains the original executable and game files in a shorter `DrDangerous` drawer. Its `savedata` directory is restored from and copied back to `WHDSaves:DrDangerous` on normal exit.
- Metropolice and +=+ have standalone launchers and self-contained drawers. Metropolice includes its external data and MP3 file.
- Hoodlum, Interpol and TRSI use the same generic Kickstart 1.3 slave as the existing Paradox Future Bike entry, with `DATA=data CUSTOM=intro`. Nitro runs its original disk 1 executable directly with `killaga`; the generic wrapper failed its launch check.
- The F1GP package uses `CUSTOM1=1` to skip the intro and retains its supplied slave and modified data under a unique `F1GP16FPS` drawer, keeping its files separate from the original game. This is specifically the 2018 competition modification, including changed car graphics, cockpit, sounds and gearing as well as the frame rate.

### Packaged archive SHA-256

- `game/Citadel_v1.4_RemonsteredEdition.lha`: `84d1f0f914b37a04cdaffff68ade1d39552f9c673d593bec8d6d11532cc1a8fa`
- `game/Connect_v1.0_Game_v1.6.lha`: `b49a50af63822ed997a4bf4a996479440a38c2445a806ab406dfcc08a261d17c`
- `game-notwhdl/BattleDuel.lha`: `039f050589bc94d13b35f201ffe67dd638e8f48980e4ed9fc0907bc343c9a240`
- `game-notwhdl/SuperDodge.lha`: `383d10ac9a57f1ff6e09acd9e62a73021dfb4753523a9c3578d5c7cc1a3b94c3`
- `game/NEONnoir_v1.0_AGA_MULTI3.lha`: `8df5a59e6be0b2e5a3890e995b70fa33d5e3d6a13505f3145904734dc9ca2f3a`
- `game-notwhdl/DrDangerous.lha`: `7932b3d783caaf4ade68970ca0432a5bba48130c30be06be608eb9ffcd39bd2a`
- `demo-notwhdl/Spreadpoint-PlusEqualsPlus.lha`: `bd5b51b654f7a3704d7019c53008aa77dde88e90e51628550cf48a07b6ff8e68`
- `demo-notwhdl/GhostownRNO-Metropolice-060.lha`: `01b05b69931db62a8d3cc46b8b0e94a6946d4aad4a24c22fd65ca969777a8834`
- `demo/HoodlumCaribbeanDisaster_v0.1.lha`: `7bd109eaad5eed9da51ab4ad52561ecb92dd4ca72502736bc4a5971bf86b6bc9`
- `demo-notwhdl/Horizon-Nitro.lha`: `890b68d008d4c2e075c1930a23d2f2a9769a83deaf7d0b8830c65d89fef28440`
- `demo/InterpolFlashback_v0.1.lha`: `d2d0c6fb53620e9c24fc0a729dda28f6ffa6f3bcea0cd31024b8de73c918aee5`
- `demo/TRSIHistoryLine_v0.1.lha`: `adb87292cd3296a21b5595ffef48bc8b84f19f75f92ce05ffc4287f04a4ce424`
- `game/FormulaOneGrandPrix16FPS_v1.0_2018Compo.lha`: `9e4615a5c3720fe11e50c6d2d2ce8ea1e7e6728317381b0bccee1014b2f8b6bf`

### Artwork sources

Connect, NEONnoir and Dr. Dangerous use screenshots from their author pages. BattleDuel uses its supplied AGA title image. SuperDodge uses a screenshot captured from its native launch in the isolated emulator. The four cracktros use the Janeway screenshots linked above; +=+ and Metropolice use their Pouet screenshots.

Citadel: Remonstered and the F1GP 16 FPS modification use screenshots captured from their packaged installs in the isolated emulator. Citadel includes both its main menu and a loaded level; F1GP shows the updated driver selection screen.

### Verification of the additional requests

All 13 additional entries reached their title/menu, gameplay or demo display in an isolated Amiberry installation. Citadel also loaded a playable level. F1GP passed its manual prompt with an arbitrary word and reached the modified driver selection screen. BattleDuel's first run requires choosing a screen mode and accepting its default preferences. Nitro was verified with the final native launcher after rejecting the generic WHDLoad wrapper.

All 18 new entries across both batches passed manifest, archive layout, installed archive hash and artwork presence checks. Native launchers match their copies in the external library. The indexer rediscovers all new IDs, the SQLite cache is refreshed, and ECS artwork is generated. Megademo 2000 and Metropolice are included in the 060 Demos list. The anniversary Worms title omits "The" for display length.

These are basic launch checks, not full playthroughs or save-cycle tests. The first five entries still require runtime testing, and 060 performance still needs appropriate hardware validation. No issues have been closed.
