# AmigaVision CD32 Setup for MiSTer 

This is a convenience package that will allow you to load Amiga CD32 games using the MiSTer Amiga core. It uses MiSTer’s MGL support allowing you to start games directly from the MiSTer menu.

## Features

* Stand-alone setup that doesn't have any dependencies on AmigaVision itself. If you want to just have CD32 games, and not the rest of the Amiga library, you can. (…and you'd be missing out on all of the good games!) 😄
* Allows you to start CD32 games directly from MiSTer's menu without requiring a mouse or keyboard, gamepad/joystick is all you need.
* No need to keep track of which games need FastMem or Instruction Cache disabled — or even that one game that requires volume control to be disabled! — we handle it for you.
* Uses AmigaVision's scanline and shadow masks presets.
* Uses AmigaVision's scaling presets, which are considered the best in the business. 😅
* Games that can make use of AmigaVision's 5×PAL overscale presets — like Chaos Engine CD32 — now use that on a per-game basis when a game can handle it. More info on this: [https://amiga.vision/5x]

## Installation

First, you need to pick the correct set of config files. Because of the way MiSTer implements paths differently between using SD cards, external USB drives, and network drives (NAS/CIFS), you need to pick the one that matches your setup.

* Open the SD, USB or NAS folder, depending on your setup.
* Copy everything inside that folder to the root of your MiSTer filesystem.

### Previous CD32 Setup

* If you already have AmigaVision installed, some files like the `Presets`, `Filters` and `Shadow_Masks` will already exist — you can skip these or overwrite them, it doesn't matter, they are identical.
* If you had the previous CD32 setup, absolutely overwrite the old `CD32.hdf` for this new setup to work.

## Upgrading

As is the case with the main AmigaVision setup, the same goes for this CD32 setup — always do a clean install and replace all the files with the exception of your `CD32-Saves.hdf`. We will update config files when needed, so you want the latest version of all the files, even though it might not be obvious what has changed from the directory listing alone.

## Adding Games 

Put your CD32 disc images in the `games/AmigaCD32` directory. You have to use the MiSTer CD32 CHD pack, or rename your own CHD images according to the naming scheme for the MGLs to work. The expected names are listed at the bottom of this file. We do not support `bin/cue` or `ISO` files.

## Playing a Game

* Navigate to `Console` → `Amiga CD32 Games`
* Select the game you want to play.
* Enjoy your game!

## Optional

If you already had the previous AmigaVision CD32 support, you can delete the `_Consoles/Amiga CD32.mgl` file — it is no longer needed, and in fact will not do anything useful if you start it.

## Compatibility

This is not a *real* CD32 core for the MiSTer. It uses the CD Audio support that was recently added to the Amiga (Minimig) core, and uses a program called CD32-Emulator to run CD32 games. 

Compatibility is not perfect, and not all games will work or necessarily have their CD soundtracks. An updated compatibility list with any special settings required can be found at:

[https://amiga.vision/cd32]

—AmigaVision Team

## File Naming Convention

Here are the file names that the setup expects for it to work properly — without these filenames, the game will not launch:

```
Alfred Chicken (1993).chd
Alien Breed - Tower Assault (1994).chd
Alien Breed 3D (1995).chd
Alien Breed Special Edition (1994).chd
All Terrain Racing (1995).chd
Arabian Nights (1993).chd
Arcade Pool (1994).chd
Banshee (1994).chd
Base Jumpers (1995).chd
Beavers (1994).chd
Beneath a Steel Sky (1994).chd
Benefactor (1994).chd
Black Viper (1996).chd
Brian the Lion (1994).chd
Brutal - Paws of Fury (1995).chd
Brutal Football (1994).chd
Bubba 'N' Stix (1994).chd
Bubble and Squeak (1994).chd
Bump 'N' Burn (1994).chd
Castles II - Siege & Conquest (1993).chd
Chambers of Shaolin (1993).chd
Chaos Engine (1994).chd
Clockwiser (1994).chd
Clou! (German) (1994).chd
Clue! (1994).chd
D-Generation (1993).chd
Dangerous Streets (1993).chd
Darkseed (1994).chd
Death Mask (1994).chd
Deep Core (1993).chd
Dennis (1993).chd
Diggers (1993).chd
Disposable Hero (1994).chd
Dizzy Collection (1994).chd
Donk! The Samurai Duck! (1993).chd
Emerald Mines (1994).chd
Exile (1995).chd
F17 Challenge (1993).chd
Fears (1995).chd
Fields of Glory (1994).chd
Fightin' Spirit (1996).chd
Final Gate (1997).chd
Fire Force (1993).chd
Flink (1994).chd
Fly Harder (1993).chd
Frontier - Elite II (1994).chd
Fury of the Furries (1994).chd
Global Effect (1994).chd
Gloom (1995).chd
Grandslam Gamer Gold Collection (1995).chd
Guardian (1995).chd
Gulp! (1994).chd
Gunship 2000 (1994).chd
Heimdall 2 (1994).chd
Humans (1994).chd
Humans 3 (1997).chd
Impossible Mission 2025 (1994).chd
International Karate + (1994).chd
James Pond 2 - Robocod (1993).chd
Jetstrike (1995).chd
John Barnes European Football (1993).chd
Jungle Strike (1994).chd
Kang Fu (1996).chd
Kid Chaos (1994).chd
Kingpin - Arcade Sports Bowling (1995).chd
Labyrinth of Time (1994).chd
Lamborghini - American Challenge (1994).chd
Legends (1996).chd
Liberation - Captive II (1994).chd
Litil Divil (1994).chd
Lunar-C (1993).chd
Magic Island (Czech) (1995).chd
Manchester United - Premier League Champions (1994).chd
Marvin's Marvellous Adventure (1995).chd
Mean Arenas (1993).chd
Microcosm (1994).chd
Morph (1993).chd
Naughty Ones (1994).chd
Nick Faldos Championship Golf (1994).chd
Nigel Mansell's World Championship (1993).chd
Oscar (1993).chd
Overkill (1993).chd
PGA European Tour (1994).chd
Pinball Fantasies (1993).chd
Pinball Illusions (1995).chd
Pinball Prelude (1996).chd
Pirates! Gold (1993).chd
Prey - An Alien Encounter (1993).chd
Project-X (1993).chd
Projekt Lila (German) (2016).chd
Quik the Thunder Rabbit (1994).chd
Rise of the Robots (1994).chd
Road Avenger (AGA) (2018).chd
Roadkill (1995).chd
Ryder Cup by Johnnie Walker (1993).chd
Sabre Team (1994).chd
Seek & Destroy (1993).chd
Seven Gates of Jambala (1993).chd
Shadow Fighter (1995).chd
Simon the Sorcerer (1994).chd
Soccer Kid (1994).chd
Soccer Superstars (1995).chd
Speedball 2 (1995).chd
Speris Legacy (1995).chd
Striker (1994).chd
Strip Pot (1994).chd
Subwar 2050 (1994).chd
Summer Olympix (1994).chd
Super Methane Bros (1994).chd
Super Skidmarks (1995).chd
Super Stardust (1994).chd
Super Street Fighter II Turbo (1995).chd
Superfrog (1994).chd
Surf Ninjas (1993).chd
Syndicate (1995).chd
Theme Park (1995).chd
TimeGal (AGA) (2017).chd
Top Gear 2 (1994).chd
Total Carnage (1994).chd
Trivial Pursuit (1994).chd
Trolls (1993).chd
UFO - Enemy Unknown (1994).chd
Ultimate Body Blows (1994).chd
Vital Light (1994).chd
Whale's Voyage (1994).chd
Wild Cup Soccer (1994).chd
Wing Commander (CD32 Enhanced) (1993).chd
Worms - Director's Cut (1995).chd
Zool (1993).chd
Zool 2 (1994).chd
```

[https://amiga.vision/5x]:https://amiga.vision/5x
[https://amiga.vision/cd32]:https://amiga.vision/cd32