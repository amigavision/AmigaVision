# Individual game additions, October 2026

Configuration and static validation only. No emulator was launched for this batch. Runtime behavior remains unverified until manual testing.

Heart of the Alien (#270) is deferred at the user's request. Digger Remastered (#245) is excluded because the requested SDL port requires RTG; the existing Justin Leck Digger entry is a different game.

## Manual test list

| Issue | Launcher title | Test |
| --- | --- | --- |
| [#390](https://github.com/amigavision/AmigaVision/issues/390) | Extreme Violence | Start a two-player match with two joysticks. Check K switches player 1 to keyboard. Esc should return to the launcher. |
| [#390](https://github.com/amigavision/AmigaVision/issues/390) | Dogfight (Richard Ling) | Reach a match and test both players, fire and flight controls. Confirm return to the launcher. |
| [#321](https://github.com/amigavision/AmigaVision/issues/321) | Daylight Robbery (Preview) | Reach a playable level and check controls. This preserved release is labelled a playable preview; verify its content before closing #321. |
| [#320](https://github.com/amigavision/AmigaVision/issues/320) | Arazok's Tomb | Confirm the BASIC runtime opens the adventure rather than an empty editor. Enter a command, then save, exit and reload. Verify DEL exits WHDLoad. |
| [#319](https://github.com/amigavision/AmigaVision/issues/319) | Imperial | Start a board, change language/preferences and quit normally. Relaunch to confirm scores/preferences persist. Save and reload a game in WHDSaves:Imperial. |
| [#294](https://github.com/amigavision/AmigaVision/issues/294) | Global Effect | Complete the startup options, start a scenario and play briefly. Save, exit and relaunch to check persistence. Confirm menu/graphics recovery on return. |
| [#293](https://github.com/amigavision/AmigaVision/issues/293) | Fields of Glory | Use an AGA setup. Start a battle, test language selection and save/load. Relaunch to confirm persistence and no FOG1:/FOG2: disk prompts. |
| [#258](https://github.com/amigavision/AmigaVision/issues/258) | Wolfen: Die Bestie ist unter uns | Reach the German adventure and progress through locations requiring later-disk data. Test save/load and DEL exit; check that no disk swaps are requested. |
| [#238](https://github.com/amigavision/AmigaVision/issues/238) | Beetle | Start one- and two-player modes. Check fire-to-jump, a bonus game and level transitions. Esc on the title screen should quit; also test DEL. |
| [#232](https://github.com/amigavision/AmigaVision/issues/232) | Gauntlet (Atari ST Port) | Use a fast CPU with Kickstart 3.0+. Press Return to add a player, use arrows to choose character/control and test both players. Check speed and return to launcher. |
| [#177](https://github.com/amigavision/AmigaVision/issues/177) | Starflight II: Trade Routes of the Cloud Nebula | Start a new game, create a crew, save, exit and relaunch. Confirm the saved game loads and no floppy prompts appear. |

## Packaging

- Extreme Violence uses the complete registered v7.23 release, which its included author documentation makes freely available. The one-player practice executable and documentation are retained. No ROM or unrelated game from the author's emulator bundle is included.
- Dogfight is Richard Ling's PD v1.1, extracted from its ADF. It is a separate entry from the existing MicroProse Dog Fight.
- Daylight Robbery retains the preview executable and all level graphics. After the native launch failed manual testing, it was moved into a Workbench 1.3 WHDLoad container, with `SAVEDIR=DaylightRobbery NOCACHE`. The startup runs DayRob_Action in the original relative directory layout. This revised launch still needs manual testing. Its title and note identify the preview status.
- Arazok's Tomb uses its supplied BASIC interpreter and game project inside the Workbench 1.3 WHDLoad slave supplied with the Beetle package. Its startup invokes `Abcc "Arazok's Tomb"`; this launch path is a priority for manual verification.
- Imperial retains v2.65 and all language, music, guide and data files. The configured base image already contains its required reqtools.library.
- Global Effect follows its supplied hard-disk layout: disk 1 executable/configuration/scenarios and disk 2 interleaves/segues/scenarios. The English language files already present on disk 1 are retained. The original Run_Game script and startup selector are used with temporary Global_Disk1:/Global_Disk2: assigns.
- Fields of Glory combines the AGA game and English/French/German files with disk 2 resources, matching its original hard-disk installer. Temporary FOG1:/FOG2: assigns replace floppy volumes.
- Wolfen combines all three disks' data and screens without conflicting filenames. Its supplied resident crack runs inside the Workbench 1.3 WHDLoad container rather than patching the launcher's running OS. The separate copyright animation is omitted from startup.
- Beetle retains the supplied WHDLoad data and Workbench 1.3 slave, renamed to Beetle.slave. Its supplied startup runs Beetle.game directly.
- Arazok's Tomb, Wolfen, Beetle and Daylight Robbery have explicit, distinct SAVEDIR values to separate their saves despite sharing the generic slave.
- Gauntlet uses the complete native Atari ST port v0.2, including the author's controls/readme. It requires Kickstart 3.0; a faster CPU is recommended.
- Starflight II follows its supplied hard-disk installer: SF2 plus DiskA, DiskB and Save directories. The floppy crack intro and OS startup files are excluded.
- Imperial, Global Effect, Fields of Glory and Starflight II seed complete writable game folders under WHDSaves: on first launch and subsequently run from those persistent folders. This preserves writes without guessing every save/config filename. Existing folders are retained on subsequent launches.

## Archive sources and SHA-256

- `game-notwhdl/ExtremeViolence.lha`: `ced9f6af074c076d7a2d828a56eddc361279605fb5135efc8ea1e4620c2fbbc4`
- `game-notwhdl/DogfightPD.lha`: `84f57d13690e775f59cdf3e134e2311296ca6c5907c0c839365e84969fd25cd8`
- `game/DaylightRobbery.lha`: `b032bc7ffbf60ab96fa50d9d04ae81f6e789886ea1ee9c75cd376e747e949b69`
- `game/ArazoksTomb.lha`: `9f0d3bc102547b80f548286edce587aa2a69ad8cc6bfc6361eac4d41acee448b`
- `game-notwhdl/Imperial.lha`: `c18c6e66ec07dc01f8a66994b89a245ed384cb077fc3b304a78c356e68bde397`
- `game-notwhdl/GlobalEffect.lha`: `baac197ca8e47bc5ede5b85597052cc33622f635a7a92d2f103f59ca00e50fc2`
- `game-notwhdl/FieldsOfGloryAGA.lha`: `a00b0b06b9f12a3356e2214b7d9ee42f0f10730772665c5ecb5393136ca86684`
- `game/WolfenDE.lha`: `dfc9d22c81f56e9e522d2f24e2cc2b1e19f77b95145bae793febf5fc87cb4b1a`
- `game/Beetle.lha`: `e4e52d17e934dbbaf9bcccd5d289f8c57f119193d97d32c5381820e0f6d8c505`
- `game-notwhdl/GauntletST.lha`: `7db4b6521be8922786b3ed2e6eada85a94be30214f253c3b5457ef1eab86bd14`
- `game-notwhdl/StarflightII.lha`: `90716ab7b1eaaa5146524fa5452f172a613f32999bd00fcc33f2f46ea5297936`

- Extreme Violence: [complete registered distribution](https://ftp2.grandis.nu/turran/FTP/Non%20TOSEC%20Games/HD/ExtremeViolenceV7.23_Shareware_FullRelease.lha).
- Dogfight: [PD v1.1 distribution](https://www.planetemu.net/en/rom/commodore-amiga-games-public-domain-adf/dogfight-v1-1-1996-ling-richard-pd-amos).
- Beetle: [complete install supplied in #238](https://ftp2.grandis.nu/turran/FTP/Non%20TOSEC%20Games/WHDLoad/Aladin%20WHDLG/Beetle-WHDL.lha).
- Gauntlet: [native port](http://wt.exotica.org.uk/files/test/gauntlet.lzx), [author requirements](http://meynaf.free.fr/pr/).

- [arazok.zip](https://ftp2.grandis.nu/turran/FTP/TOSEC/Games/Commodore%20Amiga%20-%20Games%20-%20%5BADF%5D/Arazok's%20Tomb%20(1987)(Aegis).zip)
- [daylight.zip](https://ftp2.grandis.nu/turran/FTP/TOSEC/Games/Commodore%20Amiga%20-%20Games%20-%20%5BADF%5D/DayLight%20Robbery%20(demo-playable)%20(1991)(Electronic%20Zoo)%5bh%20RBS%5d%5bunreleased%5d.zip)
- [fields1.zip](https://ftp2.grandis.nu/turran/FTP/TOSEC/Games/Commodore%20Amiga%20-%20Games%20-%20%5BADF%5D/Fields%20of%20Glory%20(1994)(MicroProse)(AGA)(M3)(Disk%201%20of%202)%5bcr%20PSG%5d.zip)
- [fields2.zip](https://ftp2.grandis.nu/turran/FTP/TOSEC/Games/Commodore%20Amiga%20-%20Games%20-%20%5BADF%5D/Fields%20of%20Glory%20(1994)(MicroProse)(AGA)(M3)(Disk%202%20of%202).zip)
- [global2.zip](https://ftp2.grandis.nu/turran/FTP/TOSEC/Games/Commodore%20Amiga%20-%20Games%20-%20%5BADF%5D/Global%20Effect%20v10.271%20(1992-04-15)(Millennium)(M4)(Disk%202%20of%203).zip)
- [global3.zip](https://ftp2.grandis.nu/turran/FTP/TOSEC/Games/Commodore%20Amiga%20-%20Games%20-%20%5BADF%5D/Global%20Effect%20v10.271%20(1992-04-15)(Millennium)(M4)(Disk%203%20of%203)%5bbootable%5d.zip)
- [starflight1.zip](https://ftp2.grandis.nu/turran/FTP/TOSEC/Games/Commodore%20Amiga%20-%20Games%20-%20%5BADF%5D/Starflight%20II%20-%20Trade%20Routes%20of%20the%20Cloud%20Nebula%20(1991)(Electronic%20Arts)(Disk%201%20of%202)%5bcr%20SR%5d.zip)
- [starflight2.zip](https://ftp2.grandis.nu/turran/FTP/TOSEC/Games/Commodore%20Amiga%20-%20Games%20-%20%5BADF%5D/Starflight%20II%20-%20Trade%20Routes%20of%20the%20Cloud%20Nebula%20(1991)(Electronic%20Arts)(Disk%202%20of%202).zip)
- [wolfen1.zip](https://ftp2.grandis.nu/turran/FTP/TOSEC/Games/Commodore%20Amiga%20-%20Games%20-%20%5BADF%5D/Wolfen%20-%20Die%20Bestie%20ist%20Unter%20Uns%20(1992)(Oase)(DE)(Disk%201%20of%203)%5bcr%20Shades%5d%5bf%20crack%20Backlash%5d.zip)
- [wolfen2.zip](https://ftp2.grandis.nu/turran/FTP/TOSEC/Games/Commodore%20Amiga%20-%20Games%20-%20%5BADF%5D/Wolfen%20-%20Die%20Bestie%20ist%20Unter%20Uns%20(1992)(Oase)(DE)(Disk%202%20of%203)%5bcr%20Shades%5d.zip)
- [wolfen3.zip](https://ftp2.grandis.nu/turran/FTP/TOSEC/Games/Commodore%20Amiga%20-%20Games%20-%20%5BADF%5D/Wolfen%20-%20Die%20Bestie%20ist%20Unter%20Uns%20(1992)(Oase)(DE)(Disk%203%20of%203)%5bcr%20Shades%5d.zip)
- [imperial.zip](https://ftp2.grandis.nu/turran/FTP/TOSEC/Games/Commodore%20Amiga%20-%20Games%20-%20Public%20Domain%20-%20%5BADF%5D/Imperial%20v2.65%20(1994)(Boursot,%20Jean-Marc)(PD)%5bWB%5d.zip)
- [global1.zip](https://ftp2.grandis.nu/turran/FTP/TOSEC/Games/Commodore%20Amiga%20-%20Games%20-%20%5BADF%5D/Global%20Effect%20v10.271%20(1992-04-15)(Millennium)(M4)(Disk%201%20of%203)%5bcr%20SR%5d.zip)

## Artwork sources

Arazok's Tomb, Fields of Glory, Global Effect, Wolfen and Starflight II use catalogued GameBase Amiga screenshots. Dogfight uses Dazeland screenshots; Daylight Robbery uses My Abandonware screenshots. Imperial, Beetle, Gauntlet and Extreme Violence use Lemon Amiga screenshots; Extreme Violence also retains its supplied title graphic. Sources are fitted to the existing conversion canvas before medium-resolution, high-resolution and ECS conversion. No emulator screenshots were taken.

- [Artwork source](https://www.lemonamiga.com/game/imperial-v2)
- [Artwork source](https://www.lemonamiga.com/game/beetle)
- [Artwork source](https://www.lemonamiga.com/game/gauntlet)
- [Artwork source](https://www.lemonamiga.com/game/extreme-violence)
- [Artwork source](https://www.dazeland.com/en/Amiga/Dogfight_Ling.html)
- [Artwork source](https://www.myabandonware.com/game/daylight-robbery-773)
- [Artwork source](https://ftp2.grandis.nu/turran/FTP/GameBase%20Amiga%202/Amiga%202.1/Screenshots/)

## Static validation

Archive manifests, CSV shape/unique IDs, source-to-package byte preservation, Amiga executable headers, native launcher paths and archive indexing were checked. The indexer rediscovers all 11 IDs. Installed archive/launcher hashes and the three artwork variants are checked after copying to the external library. These checks do not establish runtime compatibility, save behavior or gameplay correctness. No issues have been closed.

## Manual-test corrections

Arazok's Tomb and Wolfen now include `data/c/Stack`, the original Kickstart 1.3-compatible utility supplied with Global Effect. Their startup scripts call Stack before the game. The missing command caused Arazok's observed "unknown command stack" error. All pre-existing package files are unchanged. These revised packages require another manual test.

## Deferred after failed manual tests

Arazok's Tomb, Wolfen and Daylight Robbery still fail manual launch tests after the generic Kickstart 1.3 container changes. All three are temporarily excluded from automatic game/language menus using the database's `redundant=1` exclusion flag. Their packages, manifests and artwork remain available for further investigation. These requests are not resolved and should remain open (#320, #258 and #321). No specific runtime cause has been established. Wolfen's short launcher title remains `Wolfen`.
