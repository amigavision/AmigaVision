# AmigaVision Version History

## Upcoming Release

* Make sure you do a clean reinstall and rename your `MegaAGS-Saves.hdf` to `AmigaVision-Saves.hdf`! A lot of config settings have changed, AmigaVision will **not** work unless you install everything fresh — like you should always do! This also applies to the CD32 and Amiga 500 setups.
* Workbench now uses 216px (NTSC) & 270px (PAL) vertical resolution to use the full height on 1080p/4K screens. This includes the Amiga 600HD setup, so do a clean install of that one if you want the new settings!
* Amiga 600HD setup now has access to `AmigaVision-Saves.hdf`` in addition to the shared MiSTer drive.
* WHDLoad upgraded to version 19.1.
* Back navigation in the launcher re-enabled.

## 2024.10.10

* Internet support was added.
* Separate CD32 launcher was added to MiSTer's main core selection menu, put CD32 games in `games/AmigaCD32`.
* There is now a dedicated [section on setting up and launching CD32 games] in the documentation.
* AmigaVision launcher entry is now optional, you can add it back into the menu in "Options" if you have a MiSTer.
* Default setup is now NTSC instead of the resulting PAL → NTSC → PAL switching that was the case in the past, to cut down on any delays when booting the setup. All games will of course run in their correct PAL or NTSC resolutions (depending on origin of the game developer) as before, this is just to avoid the 1-2 second wait every time a new resolution is applied on boot. We default the launcher to NTSC for maximum compatibility with e.g. US consumer CRT TVs, since these often can't handle PAL.
* Added 1280×1024 (5:4) resolution option for Workbench
* Updated 100 NTSC games to use 5:6 PAR
* Configurations for 49 games added/updated, current with WHDLoad as of 2024.10.01.

## 2024.08.18

* Added support for booting CD32 disc images (CHD or bin/cue) on MiSTer from the launcher. 
* Dynablaster's battle mode timed out after 3 seconds instead of 3 minutes, fixed.
* Non-AGA version of Robocod added, since it is a different set of levels
* Alien Breed non-SE added, has better gamepad controls
* Various offsets/scaling imrpoved (Turrican 2, Switchblade II)
* Updated configurations to be current with WHDLoad as of 2024.08.14, games added/updated:
	* A320 Airbus 
	* A320 Airbus: Edition Europa
	* Aladdin's Magic Lamp
	* Centerbase
	* Evil's Doom
	* Evolution Cryser
	* Fortress Underground
	* Galaga
	* Glubble
	* Grand National
	* Indian Mission (German only)
	* Magic Serpent
	* Pop-Up
	* Shadow Fighter (No-jump version)
	* The Final Trip
	* Tubular Worlds
	* Wrath of the Demon (Scoopex fixed version)

## 2024.06.06

* Added optional `MiSTer.ini` settings for 1440p displays. Note that these will not use the 5×PAL Dynamic Crop, those are only active for 1080p and 4K displays.
* Sensible World of Soccer had several problems with loading tactics and English club teams in the past few releases. This was fixed upstream.
* New June update of Castlevania AGA, includes a music test menu and a new character sprite, as well as other fixes.
* Turrican 3 now supports the full set of CD32 buttons, making it much better to play with a gamepad.
* 8 games identified as running with the wrong settings, fixed.
* Game configurations are current with WHDLoad as of 2024-06-05.

## 2024.04.04

* 528 games .changed from PAL60 to PAL with 5× scaling offsets.
* 28MHz is the new default pixel clock, make sure you update the `Amiga.cfg` file.
* Revision 2024 demo party entries added.
* WHDLoad configurations are up to date with WHDLoad 2024-04-03.

## 2023.12.25

* WHDLoad configurations are up to date with WHDLoad 2023-12-23.
* Wings of Death crash on exit fixed.
* Some 5×PAL offsets/defaults improved: Turrican, Switchblade, Agony.
* Notable demo added: The Black Lotus — Eon.
* Disk Magazines added: Stolen Data 9 & 10
* Christmas version of Mega-lo-Mania added.
* "Lost" Codemasters game added: Stuntman Seymour.
* Aspect ratio fixes for several games LucasArts and Cinemaware games: Maniac Mansion, Zak McKracken, Loom, Pipe Dream, Battlehawks 1942, Who Framed Roger Rabbit, Lords of the Rising Sun, King of Chicago, It Came From the Desert, Antheads, Sinbad, SDI, Rocket Ranger, Three Stooges, TV Sports Baseball, TV Sports Football, TV Sports Boxing, TV Sports Basketball, Wings.
* New "Focus" categories: “PD Golden Age”, “PD Silver Age” — the best of Public Domain games on the Amiga.
* Requests for specific game and demo configurations for the Analogue Pocket setup added.
* Longer game names allowed in the launcher, which avoids 99% of truncated names.
* Topaz Double added to the setup for those of you wanting to run Workbench in a 1:1 pixel aspect ratio setup.
* Build script is now capable of running without any human interaction.

## 2023.07.17

* More reliable loading of thumbnail previews in the launcher when returning from a previously loaded game or demo. This was especially noticable in the Pocket variant, since that device has slower disk access.
* Zine 11 disk magazine now works.
* Disambiguation between multiple versions of the same game (e.g. ECS vs AGA) in titles ended up accidentally listing them with a language code instead. This has been fixed.

## 2023.07.07

* Direct SCSI is now enabled by default --- this improves compatibility with certain original Amiga hardware setups.
* Additional requested game configurations for the Analogue Pocket have been included.
* WHDLoad configurations are up to date with WHDLoad 2023-07-06.
* Some games have updated and improved PAL & NTSC configurations.
* Adding games with titles >30 letters as a Favorite now works.

## 2023.06.06

* Improved aspect ratio and Pixel Aspect Ratio handling to ensure 16:15 PAL and 5:6 NTSC pixels.
* Support for the Analogue Pocket FPGA
* Favorites support in the launcher
* Non-English Games Included & Categorized
* Support for Amiga 1200/4000 and CD32
* Support for emulators

## 2023.04.05

* This new version makes use of MiSTer's recently introduced `MGL` support to supply convenient, dedicated `Amiga` and `Amiga 500` setups for ease of switching on MiSTer. This lets you have the best of both worlds: An everyday, easy HD-based games/demo setup, as well as a cycle-accurate floppy-based Amiga 500 for running ADF games and demos when necessary.
* New, optional `Amiga 500HD` and `Amiga 600HD` setups are included for those of you looking to explore Workbench 1.3 and 2.x as period-accurate HD setups — these both support the MiSTer shared drive and use the PFS file system for robustness. See the `Extras` part if you are interested in these.
* Up to date with the latest WHDLoad recipes for games and demos as of 2023.03.03.
* Lots of new disk magazines and demos.
* Significantly faster load times when entering lists in the launcher.
* Jump-to-letter using keyboard in the launcher.
* Launcher now supports going to the parent list using secondary/blue/B button from a gamepad/joystick, or using backspace on the keyboard. You can enable the old behaviour with an explicit "Back" entry in `Options` if you prefer the old behavior.
* Launcher supports chronological sorting, pre-set in certain lists like "Disk magazines, by release date", which is a great way to follow the history of the Amiga demo scene in the 90s, as written by the demo scene members.
* Natural sorting: the launcher will now sort e.g. Turrican, Turrican II, Turrican 3 in that order instead of a straight ASCII sort.
* New "look and feel" for the launcher.
* MiSTer Super Attract Mode integration added.
* `AmigaVision-Extras` section added, with alternative MGL based configs and convenient PFS-formatted `Saves` HDF images in various sizes. See the dedicated documentation included for more detail.

## 2022.06.06

* Experimental MiST & CD32 hardware compatibility
* Joystick/gamepad support for selecting game options from WHDLoad dialog
* Eurochart #1-48 disk magazines added
* Additional (and updated/fixed) 5×PAL settings
* [WHDLoad] updates

## 2022.03.03

* Quick update to address some erroneous 5×PAL settings

## 2022.02.02

* 500+ additional per-game 5×PAL scale settings
* New 6× scaling mode for 16:9 demos
* MT-32 MIDI game support
* New custom 40:27 aspect ratio

## 2021.03.13

* Introduced per-game 5×PAL dynamic crop for 1200+ games, see https://amiga.vision/5x for full details

[WHDLoad]:http://whdload.de/news.html

## 2020.11.16

* RTG support for high-resolution graphics up to 1920×1080 in Workbench
* WHDLoad updates

## 2020.05.16

* Disk Mag category added
* Crack Intro category added
* WHDLoad updates

## 2020.05.05

* Support for the HD720 graphics driver, up to 720p using the original AGA chipset
* WHDLoad updates

## 2019.10.09

* Initial release of AmigaVision
