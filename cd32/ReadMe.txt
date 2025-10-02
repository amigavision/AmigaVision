# AmigaVision CD32 Setup for MiSTer 

A ready-to-go package for playing Amiga CD32 games on MiSTer’s Amiga core.

## Features

* Fully stand-alone — no AmigaVision install required. If you only want CD32 games (although you’d be missing out on the rest of the Amiga classics! 😄), this works by itself.
* Launch CD32 games straight from the MiSTer menu — no keyboard or mouse required, just your controller.
* Forget juggling obscure settings like NoFastMem, Instruction Cache, or that one game needing Volume Control off — we handle all that automatically.
* Uses AmigaVision's scanline and shadow masks presets.
* Uses AmigaVision's scaling presets, which are considered the best in the business. 😅
* Games that can make use of AmigaVision's 5×PAL Overscale presets — like Chaos Engine CD32 — now use that on a per-game basis when a game can handle it. More info on this: [https://amiga.vision/5x]

## Installation

Simply copy the contents to the root of your MiSTer drive. For platforms that ask, you should of course Merge with the existing files, and overwrite any existing files if asked (e.g. if you already have the main AmigaVision installed, especially the ones that contain a CD32 setup). This will work for SD card and NAS (network drive) setups. 

If you are not using an external USB drive to store your game setup, you can delete `USB.7z`.

If you are using an external USB drive for storing your game setup, there is an included `USB.7z` file included that you should use instead — this unpacks in the same way as the main archive, and you copy these contents to your MiSTer USB drive instead.

## Upgrading

As is the case with the main AmigaVision setup, the same goes for this CD32 setup — always do a clean install and replace all the files with the exception of your `CD32-Saves.hdf`. Configuration files may change over time, even if it’s not obvious from the folder listing — always replace them to stay up to date.

### Previous CD32 Setup

* If you already had AmigaVision installed, some files like the `Presets`, `Filters` and `Shadow_Masks` will already exist — you can skip these or overwrite them, it doesn't matter, they are identical.
* If you had the previous CD32 setup, be sure to overwrite the old `CD32.hdf` for this new setup to work.
* If you already had the previous AmigaVision CD32 support, you can delete the `_Consoles/Amiga CD32.mgl` file — it is no longer needed, and in fact will not do anything useful if you start it.


As usual, when in doubt, overwrite. **Except for your save files.**

## Adding Games 

Put your CD32 disc images in the `games/AmigaCD32` directory. You have to use the MiSTer CD32 CHD pack, or rename your own CHD images according to the naming scheme for the MGLs to work. 

The expected names are listed at the bottom of this file. We do not support `bin/cue` or `ISO` files. Because why would you want to waste space like that? 😅

## Playing a Game

* Navigate to `Console` → `Amiga CD32 Games`
* Select the game you want to play.
* Enjoy your game!

## Mapping Controller Inputs

Some Amiga CD32 games are up-to-jump or up-to-accelerate, which is OK if you have a joystick, but might be awkward if you use a gamepad. Consult MiSTer's documentation to remap buttons for these games.

## Game Recommendations

The CD32 wasn't exactly a paragon of a console with incredible games, and was cut short by Commodore's unfortunate bankruptcy before it could really prove itself. However, if you are looking for a starting point, here are some games to check out:

* **Fightin' Spirit** — Probably the best Street Fighter 2 clone on the Amiga.
* **Chaos Engine** — True Amiga classic, two-player mode is especially fun.
* **Beneath a Steel Sky** — Great point & click adventure in the Lucasfilm style with voice acting — does require a mouse, though.
* **Super Stardust** — Enter `BZZZZZZZZZB` to jump straight to its iconic tunnel sequence.
* **Worms** — This legendary game series got its start on the Amiga.
* **Pinball Fantasies** — Move over, every 16-bit pinball game created! This is the one that set the standard.
* **Fury of the Furries** — Great platform game. This game is up-to-jump, which works great with joysticks, but remap in MiSTer if you have a gamepad.
* **Banshee** — Great shoot'em-up, and the pixel art is next-level.
* **Flink** — Did someone say pixel art? Gorgeous platformer.
* **Disposable Hero** — Surprisingly good shoot'em-up.
* **Naughty Ones** — Late-stage platformer made by one of the most influential Amiga demo groups.
* **Speedball 2** — Does not have the iconic music of the original Amiga version, but new voice-over and great ambient soundscapes makes this a great 2-player experience.
* **Super Skidmarks** — Great overhead racer. If you loved RC Pro-AM on Nintendo, you will love this.
* **Superfrog** — Every system needs a mascot platformer, right? This game is arguably the one for Amiga. Ignore Zool, play this instead.

## Fun Facts

* We generate 1280 config files to ensure these CD32 games work on MiSTer.
* We generate 10 different hard disk images to power these.

## Games Where You Need to Select "Boot" to Start

There are some games that won't work unless we show the Amiga UI first, but we supply mouse emulation for gamepads — just navigate to the "Boot" button to start these:

* Arabian Nights 
* Arcade Pool 
* Fields of Glory 
* Fire Force
* Kid Chaos 
* Marvin's Marvellous Adventure
* Nigel Mansell's European Championship
* Rise of the Robots
* Trivial Pursuit
* Vital Light
* Zool
* Zool 2

## Games That Still Require a Mouse

There are a few games that still require mouse because the game demands it. These are:

* Beneath a Steel Sky 
* Gulp
* Magic Island
* Seek & Destroy
* Syndicate
* Theme Park

(If you can't start a game with the gamepad by navigating to the "Boot" button, it's a definitely a game that requires a mouse to play.)

## Games That Can Use 5xPAL Overscale

As you may know, AmigaVision has per-game [5×PAL Overscale presets] for games that support it, which optimizes scaling for 1080p/4K. With this setup, we are bringing that same support to CD32!

The following games will use 5×PAL Overscale:

* Arabian Nights
* Beavers
* Beneath a Steel Sky
* Black Viper
* Brian the Lion
* Brutal Paws of Fury
* Brutal Football
* Bubba N Stix
* Castles II - Siege & Conquest
* Chambers of Shaolin
* Chaos Engine
* D/Generation
* Darkseed
* Death Mask
* Dennis
* Diggers
* Disposable Hero
* Emerald Mines
* Exile
* Fields of Glory
* Fire Force
* Flink
* Fly Harder
* Frontier - Elite II
* Fury of the Furries
* Global Effect
* Guardian
* Gulp
* Gunship 2000
* Heimdall 2
* Humans
* Impossible Mission 2025
* International Karate
* James Pond 2 - Robocod
* John Barnes European Football
* Jungle Strike
* Kid Chaos
* Labyrinth of Time
* Lamborghini American Challenge
* Legends
* Lotus Trilogy
* Marvin's Marvellous Adventure
* Nigel Mansell's World Championship
* PGA European Tour
* Pirates Gold
* Projekt Lila
* Road Avenger
* Roadkill
* Ryder Cup by Johnnie Walker
* Seven Gates of Jambala
* Soccer Kid
* Speedball 2
* Strip Pot
* Subwar 2050
* Summer Olympix
* Super Street Fighter II Turbo
* Surf Ninjas
* Syndicate
* Theme Park
* Time Gal
* Top Gear 2
* Total Carnage
* Trolls
* UFO - Enemy Unknown
* Vital Light
* Whale's Voyage
* Wild Cup Soccer
* Wing Commander

## Compatibility

This is not a *real* CD32 core for the MiSTer. It uses the CD Audio support that was added to the Amiga (Minimig) core, and uses a program called CD32-Emulator to run CD32 games. 

Compatibility isn’t perfect — some games may not work or may lack their CD audio tracks. An updated compatibility list with any special settings required can be found at:

[https://amiga.vision/cd32]

*—AmigaVision Team*

## Addendum: File Naming Convention

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
Worms (1995).chd
Zool (1993).chd
Zool 2 (1994).chd
```

[https://amiga.vision/5x]:https://amiga.vision/5x
[https://amiga.vision/cd32]:https://amiga.vision/cd32
[5×PAL Overscale presets]:https://amiga.vision/5x
