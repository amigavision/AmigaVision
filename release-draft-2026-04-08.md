---
title: AmigaVision 2026.04.16 Updated with Massive Platform Expansion, Fixes 30-year Amiga Emulator Scaling Issues, adds 2,955 Game Manuals + 137 New Games and Demos
published: false
---

We are happy to announce that a new version of [AmigaVision] is available!

AmigaVision is the ultimate Amiga games *&* demo scene setup for MiSTer *&* Pocket FPGAs, Raspberry Pi + emulators, and real Amiga hardware.

To find out more, visit the [AmigaVision](https://amiga.vision) site.

## ✅ Summary

* **Support for every major platform** — AmigaVision now has dedicated support and documentation for original Amiga hardware, MiSTer and Analogue Pocket FPGAs, Raspberry Pi, and desktop emulator setups on Mac, Windows, and Linux, well as handheld emulation, including iOS and Android.
* **30-year old scaling issues in Amiga emulators fixed** — NTSC scaling has been broken in every Amiga emulator since the introduction of Amiga emulation 30 years ago. This release of AmigaVision fixes that.
* **Overscale support in emulators** — The emulator support now lets you use AmigaVision's overscale support to experience Amiga games in 16:9, 16:10 or even 21:9 without stretching the image, and while doing integer scaling, every pixel is kept intact.
* **2,955 QR codes linking to game manuals added** — We have added links to pretty much every commercially published Amiga game with a manual, linking directly to online versions, perfect for loading those game manuals on a phone or a tablet while you are simultaneously playing the game.
* **Metadata improvements** — compared to the last release, **2,885 existing entries** have newly updated metadata, covering everything from genres, IDs, and short names to hardware labels, regional flags, and launcher-facing cleanup.
* **Expanded demo scene section** — In addition to many new productions, the launcher now includes curated demoscene lists like **H0ffman’s Picks**, a dedicated **060 Demos** section, and expanded **Widescreen** demo support.

## 🌍 AmigaVision on Every Platform

One of the biggest news in this release is adding a ton of new supported platforms for AmigaVision.

### The project now explicitly supports and documents:

* **Original Amiga Hardware** — A simple write to an SD or CF card gets you up and running in minutes.
* **Mac, Windows, and Linux** — Finally bringing automatic integer-scaled, auto-cropped PAL *&* NTSC [overscale](https://amiga.vision/overscale) and correct [NTSC PAR](/ntsc) scaling to Amiga emulators for the first time in the 30-year history of Amiga emulation.
* **Raspberry Pi** — Specifically tuned to deliver best-in-class low input, output, and audio latency — lower latency than any other Raspberry Pi setup.
* **Analogue Pocket** — Handheld FPGA Amiga on the go? We have the only Amiga setup for this handheld available.
* **iOS and Android** — Play your Amiga games on the go, and watch the latest demo scene productions anywhere.
* **MiSTer FPGA** — the [best Amiga available in 2026](/best), and where the project originated.

## 30-year old scaling issues in Amiga emulators fixed

If you know anything about the AmigaVision project, you know that we care about two things above all else: low video/audio/input latency, and correct Amiga scaling.

Amiga emulators have gotten NTSC scaling on the Amiga wrong ever since their start over 30 years ago. They have shown NTSC Amiga games with a 1:1 Pixel Aspect Ratio (PAR) since the very beginning. You have been able to adjust this manually if you know what you are doing, but they have never done this automatically for you. 

In addition, if you want to switch between NTSC and PAL games — the majority of Amiga games are PAL, but many super influential early games on the Amiga like Defender of the Crown, Wings, Marble Madness *&* Monkey Island are NTSC — you would have to do per-game setups to get it right, and most people were not aware of this, nor knew how to configure it.

Amiga NTSC uses a 5:6 PAR (according to how most people adjusted their NTSC monitors and TVs) or 6:7 PAR (according to the NTSC spec that was rarely implemented correctly on Amiga on consumer TVs) like we describe and show in [our description of this](https://amiga.vision/ntsc).

This results in a lot of people experiencing art in the wrong format, especially early titles e.g. the ones with artwork by the legendary Jim Sachs (Defender of the Crown, Ports of Call):

<figure class="compare before" id="dotc-compare">
  <div class="compare-stack">
    <img src="https://amiga.vision/images/dotc-ntsc.png" alt="NTSC" data-caption="NTSC" class="is-active">
    <img src="https://amiga.vision/images/dotc-pal.png"  alt="PAL"  data-caption="PAL">
  </div>
  <figcaption class="compare-caption">NTSC</figcaption>
</figure>

As you can see, this results in people looking much wider than they are, and mis-represents the original intent of the artist.

NTSC on the Amiga (and DOS PCs!) should never use 1:1 pixel aspect ratios.

AmigaVision fixed this on the MiSTer FPGA platform in 2021, but this has never been available to Amiga emulators running everywhere else.

We have worked with the author of the [Amiberry](https://amiberry.com) Amiga emulator over the past 2 years to address this and many other scaling issues in Amiga emulators. Many large spreadsheets and voice calls were involved, but we got there in the end.

AmigaVision now offers correct NTSC PAR scaling in resolutions that are capable of doing so, which is any display from 800p and upwards to 8K displays.

*Amiberry is now the first Amiga emulator in the 30-year history of Amiga emulation to get this right without requiring per-game manual adjustments.*

We hope and suspect that this scaling approach will also soon come to other Amiga emulators like WinUAE, `puae` and other emulators — but as of this release, AmigaVision has switched to using Amiberry for its Mac, Linux and Windows implementations, since it is the only one that offers correct NTSC scaling and simultaneously does integer scale autocrop properly — all out of the box without you having to configure anything.

There will be a more comprehensive write-up in the near future, but if you want to see us explain the details of how it works, we were recently on a [livestream with AmigaBill](https://www.twitch.tv/videos/2746470548?t=00h26m38s) where we go into detail about it, and the history of Amiga emulator scaling.

(We will endeavour to work with the remaining dominant Amiga emulators to help out there too, so hopefully this can be fixed everywhere soon!)

## 16:9 Widescreen *&* 21:9 Ultrawide Scaling for Emulators

Did you know that many Amiga demos *&* games — despite running on a platform from 1985 — are designed to run in 16:9 or 16:10 aspect ratios? Or even 21:9 aspect ratios? Truly a computer ahead of its time.

In 2021, we implemented support for 16:9 and 16:10 scaling on MiSTer by adding [5×PAL Overscale](https://amiga.vision/overscale), which makes Amiga games use overscaling automatically on a per-game basis without any manual configuration. While most emulators use 4×PAL scaling, AmigaVision has per-game 5×PAL scaling. The result looks like this on modern 16:9 displays:

![5x scaling](https://amiga.vision/images/gods5x.gif)

![5x scaling](https://amiga.vision/images/flashback5x.gif)

With this release of AmigaVision, we are bringing 16:9, 16:10 — and even 21:9 Ultrawide cinematic aspect ratio scaling for games and demos that support it, like the intro to Pinball Illusions from 1995:

<iframe style="aspect-ratio: 16/9; width: 100%;" src="https://www.youtube.com/embed/I7ONAsXM9Gk" title="YouTube Video Player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

This is *not* stretching anything, this is not doing any interpolation scaling, it is *integer-scaled original pixels* with a smart cropping algorithm, maintaining the original output.

So with today's release, people can experience 16:9, 16:10, and 21:9 Amiga content on emulators too, like this 21:9 Ultrawide demo by Logicoma from 2025, which will display full-width on displays like 1440p and 5K2K 21:9 displays:

<iframe style="aspect-ratio: 16/9; width: 100%;" src="https://www.youtube.com/embed/h-K7a3B9Leg" title="YouTube Video Player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

This, again, is possible only because of the scaler fundamentals we established with our work with the author of [Amiberry](https://amiberry.com) — Dimitris Panokostas — and most of the Amiga emulator audience has never seen these 16:9 and 21:9 Amiga visual presentations delivered in their optimal formats. Now, with the latest AmigaVision, they will.

## 📚 2,955 Game Manuals Added

Thousands of games in the AmigaVision launcher now let you jump straight to controls, reference material, and documentation directly from the launcher instead of hunting for game manuals manually. Check out this example from the launcher, and try it on your phone/tablet!

![Entry for Airborne Ranger showing link to QR code that brings you to the game manual](https://amiga.vision/images/qr-example.jpg)

These are explicitly pointing to QR links instead of loading on the Amiga itself, so you can have them open on secondary devices while you play Amiga games on your main display.


## 💾 Expanded Real Hardware Support

We have worked hard on supporting real Amiga hardware in the best possible way in this release:

* **68040/68060 accelerator support** via **Mu680x0Libs** has been added.
* **PCMCIA CompactFlash + SD support** for easier file transfer and storage on real Amiga setups was also added.

## 💿 Standalone CD³² MiSTer Setup Improvements

The [CD32](/cd32) work since the previous major release is substantial.

* **CD32 is now treated as a proper standalone setup on MiSTer** rather than just a launcher add-on.
* **Per-game autoloading MGL generation and packaging has been improved**, including better SD/USB/NAS handling.
* **NAS / CIFS network-share setups are now included for CD32 users**, resolving a long-standing request from people running their CD32 collection from SMB shares.
* **Per-game [5×PAL Overscale](/overscale) presets have been added for CD32 titles**, along with compatibility variants for games that need different `NoFastMem`, `ICache`, or other special setups.
* **A large number of CD32-specific compatibility fixes have landed**, including changes for titles such as D/Generation, Disposable Hero, Bubble and Squeak, Gulp, Seek & Destroy, Rise of the Robots, Road Avenger, TimeGal, Zool, Zool 2, Impossible Mission, Gunship 2000, Pirates! Gold, and the newly added **Castlevania AGA** setup.

## 📡 BBS *&* Online Features

AmigaVision's online and BBS features were also improved:

* **Many new BBS listings were added** to the setup.
* **PPP serial speed was doubled to 230400 bps**, improving your transfer speeds online.

## 📺 PAL *&* NTSC *&* 5×PAL Overscale Fixes

Display correctness continues to be a major focus, and a lot of work has gone into getting titles to run in the right video mode with the right scaling.

The following games have had specific PAL, NTSC *&* [5×PAL Overscale](/overscale) fixes since 2025.05.05:

* **5×PAL Overscale Fixes** for Bargon Attack, Beavers, Black Viper, D/Generation, Diggers, Gulp, John Barnes European Football, Marvin’s Marvellous Adventure, Perihelion, Total Carnage, and Vital Light.
* **PAL *&* NTSC Corrections** for Barbarian II (Psygnosis), Nebulus, Panza Kick Boxing, Phobia, Super C, and the French version of Panza. We also corrected a number of Tynesoft titles that had been marked as NTSC, including Beverly Hills Cop, Formula 1 Grand Prix, Mayday Squad, Plutos, Roller Coaster Rumbler, Summer Challenge, Summer Olympiad, Winter Challenge, and Winter Olympiad 88.
* **Offset *&* Display Tuning** has also been improved for Brutal: Paws of Fury, Mr. Nutz, Ugh!, and Return of the Jedi.

## 🧹 Metadata Cleanup

A big — but somewhat invisible — improvement in this release is how much tidier the game and demo library has become.

* Since the previous release, **2,885 existing entries** have received metadata updates, spanning **2,312 unique titles**.
* That includes **2,052 game entries** and **833 demo entries** with updated metadata.
* Hundreds of titles that previously had no genre assigned now do.
* Genre labels have been simplified into cleaner categories.
* Demo scene titles with repetitive names have had better short names added, which makes lists with titles such as “Megademo X” easier to browse.
* A large number of entries have had corrected IDs, better titles, cleaner hardware labels, and generally improved metadata.

## 🕹️ 137 New Games *&* Demos

AmigaVision now contains **5,342 hand-tuned game and demo configurations** in total.

Compared to the previous release, **137 unique new titles** have been added: **91 games** and **46 demos**.

<details>
<summary><b>Expand for Full List of 91 New Games</b></summary>

<ul>
<li>A 10 Tank Killer Extra Missions</li>
<li>Abu Simbel Profanation</li>
<li>Agresor</li>
<li>Aventura Espacial, La</li>
<li>Aventura Original, La</li>
<li>Bad Dudes Vs Dragon Ninja</li>
<li>Batman</li>
<li>Blues Brothers 2 Demo</li>
<li>Breach & Data Disk</li>
<li>Bush Buck: A Global Treasure</li>
<li>Challenge Golf</li>
<li>Crime Time</li>
<li>Diabolik 01: Inafferrabile Criminale</li>
<li>Diabolik 03: La Fuga</li>
<li>Diabolik 04: Trappola D'Acciaio</li>
<li>Diabolik 06: La Notte Della Paura</li>
<li>Diabolik 07: 4 Diamanti Unici</li>
<li>Diabolik 08: Un Piano Perfetto</li>
<li>Diabolik 09: A Caro Prezzo</li>
<li>Diabolik 10: All'Ultimo Sangue</li>
<li>Diabolik 11: Inganno Fatale</li>
<li>Diabolik 12: Terrore A Teatro</li>
<li>Dig Dug 2</li>
<li>Discovery & Data Disks</li>
<li>Dungeons Of Avalon 2</li>
<li>Dylan Dog 01: La Regina Delle Tenebre</li>
<li>Dylan Dog 03: Storia Di Nessuno</li>
<li>Dylan Dog 04: Ombre</li>
<li>Dylan Dog 05: La Mummia</li>
<li>Dylan Dog 06: Maelstrom</li>
<li>Dylan Dog 07: Gente Che Scompare</li>
<li>Dylan Dog 08: La Clessidra Di Pietra</li>
<li>Dylan Dog 09: Il Male</li>
<li>Dylan Dog 10: I Vampiri</li>
<li>Dylan Dog 11: Il Marchio Rosso</li>
<li>Dylan Dog 13: I Killers Venuti Dal Buio</li>
<li>Dylan Dog 14: Il Bosco Degli Assassini</li>
<li>Dylan Dog 15: Inferni</li>
<li>Dylan Dog 17: Il Cimitero Dimenticato</li>
<li>Evils Doom</li>
<li>F 29 Retaliator</li>
<li>Fightin Spirit</li>
<li>Fire Force</li>
<li>Frutis</li>
<li>Gyrex</li>
<li>Gyruss</li>
<li>Hyper Sports</li>
<li>Hyper Wings</li>
<li>International Karate</li>
<li>Iridon</li>
<li>It Came From The Desert 2</li>
<li>Jeanne d'Arc</li>
<li>Joust</li>
<li>Kaboomania Demo</li>
<li>KC Munchkin</li>
<li>Kings Quest 5 Remastered</li>
<li>Larrie & The Ardies</li>
<li>Liberation</li>
<li>Lock N Chase</li>
<li>Mappy</li>
<li>Mouth Man</li>
<li>Movem</li>
<li>Oilmania</li>
<li>Out Run Amiga Edition</li>
<li>Outfall</li>
<li>Paladin & Data Disk</li>
<li>Piracy Deluxe</li>
<li>Piracy On The High Seas</li>
<li>Police Quest 3 Remastered</li>
<li>Powder</li>
<li>Pulsar</li>
<li>Regresja</li>
<li>Renegade AGA</li>
<li>Renegades Deluxe</li>
<li>Rogue Declan Zero</li>
<li>Rogue Declan Zero Amiga Addict Edition</li>
<li>Sensible World Of Soccer 2526</li>
<li>Side Winder</li>
<li>Space Quest 4 Remastered</li>
<li>Space Vegetables</li>
<li>Starball</li>
<li>Steve Davis World Snooker</li>
<li>The Pursuit To Earth</li>
<li>Theme Park XMAS Demo</li>
<li>Track & Field</li>
<li>US Championship V Ball</li>
<li>Vector Battleground</li>
<li>Whales Voyage</li>
<li>Works Team Rally</li>
<li>Zippy Race</li>
<li>Zzzep</li>
</ul>
</details>

<details>
<summary><b>Expand for Full List of 29 Updated Games</b></summary>

<ul>
<li>Bargon Attack</li>
<li>Beavers</li>
<li>Black Viper</li>
<li>Brutal: Paws of Fury</li>
<li>Bubble and Squeak</li>
<li>D/Generation</li>
<li>Diggers</li>
<li>Disposable Hero</li>
<li>Gulp</li>
<li>Gunship 2000</li>
<li>Impossible Mission</li>
<li>John Barnes European Football</li>
<li>Marvin's Marvellous Adventure</li>
<li>Mr. Nutz</li>
<li>Nebulus</li>
<li>Panza Kick Boxing</li>
<li>Perihelion</li>
<li>Phobia</li>
<li>Pirates! Gold</li>
<li>Return of the Jedi</li>
<li>Rise of the Robots</li>
<li>Road Avenger</li>
<li>Seek & Destroy</li>
<li>Super C</li>
<li>Total Carnage</li>
<li>Ugh!</li>
<li>Vital Light</li>
<li>Zool</li>
<li>Zool 2</li>
</ul>
</details>

## 🔥 48 New Demo Scene Productions

The demo scene continues to get love in this release, as always!

In addition to the metadata cleanup for demo scene entries, AmigaVision has added **48 new demos:**

<details>
<summary><b>Expand for Full List of 48 New Demos</b></summary>

<ul>
<li>Alcatraz — Soil</li>
<li>Andromeda — Murder Scrolls</li>
<li>Appendix — Reborn</li>
<li>The Black Lotus — Captured Dreams</li>
<li>The Black Lotus — Darkside</li>
<li>The Black Lotus — Final</li>
<li>The Black Lotus — Ocean Machine</li>
<li>The Black Lotus — Silk Cut</li>
<li>The Black Lotus — Starstruck</li>
<li>Capsule — Brutalism</li>
<li>Demostue Allstars — No CPU Challenge</li>
<li>Desire — D Funk</li>
<li>Desire — FM</li>
<li>Desire — HAMazing</li>
<li>Desire — Is Real</li>
<li>Desire — Waffles Of Math Construction</li>
<li>EPH — No Return</li>
<li>Ephidrena — Hexel</li>
<li>Ephidrena — Knarkzilla</li>
<li>FFP — Planetary Void</li>
<li>Flex — Dead Ahead</li>
<li>Flex — Martini Effect</li>
<li>Focus Design — 1992</li>
<li>Focus Design — Be Kool Fool</li>
<li>Focus Design — Revision2012</li>
<li>Ghostown & Loonies — Smoke And Mirrors</li>
<li>Ghostown — Human Traffic</li>
<li>Ghostown — Last Train To Danzig</li>
<li>H0ffman — Everyway</li>
<li>Impulse — Muscles</li>
<li>Lemon — 3D Demo 3</li>
<li>Logicoma — Entropy Chamber</li>
<li>Mystic — Impossible Possibility</li>
<li>Nature — Jesus Christ Motocross</li>
<li>Nerve Axis — Pulse</li>
<li>Nerve Axis — Relic</li>
<li>Noice — Last Goat Standing</li>
<li>Pacific — BYO 40K</li>
<li>Pattern Syndicate — Tactical Transmissions</li>
<li>Polka Brothers — Gevalia</li>
<li>Purple Studios — Fake One</li>
<li>Rift — Fari Bars</li>
<li>Spaceballs — Disiplin</li>
<li>Spaceballs — Norwegian Kindness</li>
<li>Spreadpoint & Swiss Cracking Association — TTCC (The Terra Cresta Cracktro)</li>
<li>Traction — Swookie</li>
<li>Unique — Singularities</li>
<li>Unique — Subside</li>
</ul>
</details>

This release cycle has also significantly expanded AmigaVision’s support for modern standalone scene productions that are not packaged in WHDLoad format. These now have proper metadata, screenshots, and launcher entries, which makes the newer Amiga demo scene easy to browse and enjoy.

Existing demos have also been updated for productions like **Captured Dreams**, **Darkside**, **Gevalia**, **Legalize It 2**, **Masterpieces**, and **Rampage**, alongside the large batch of new demo additions.

To help surface the best of the demoscene, the Demo section now also includes curated lists such as **H0ffman’s Picks**, a dedicated **060 Demos** category, and more **Widescreen** productions.

## 🌟 Recommended Games *&* Demos to Check Out in This Release

### Games

* Sensible Soccer fan? You can now play with the 2026 lineups of players. Always pick Erling Haaland for your team! 😄
* Want to see how Amiga deals with some arcade classics? Modern ports of **OutRun** and **Renegade** are now available.
* Running the CD32 setup on MiSTer? The modern **Castlevania** for Amiga (not a port, but a reimagining of the X68000 version) is available with a CD soundtrack in the CD32 version, and comes highly recommended if you're running our CD32 setup on MiSTer!
* Italians have it good in this release of AmigaVision, as we have added cult classic game series **Diabolik** and **Dylan Dog**, 29 games in all. Check them out if you understand Italian!
* We didn't forget our Spanish friends either, **La Aventura Original** *&* **La Aventura Espacial** have been added. If you know Spanish, check them out!


### Demos

* Fresh off the press! This year's Revision 2026 Amiga Demo winner is **Second Nature** by **Desire *&* TTE** — incredible work, 1-disk OCS Amiga 500 demo that has an incredible amount of cool effects and packs an insane amount of content into 880KB, and of course in glorious 16:9 format! One of the best ways to check out our new emulator support for 16:9 and 21:9 displays!
* If you are using emulators or have access to a real Amiga with an 060 acceleration, do check out the demos in our dedicated **060 Demos** category!
* For some hand-picked modern classics to familiarize yourself with what has been happening in the Amiga demo scene in the past years, check out **H0ffman's Picks** for some real modern classics.

## 🤝 Greetings

In traditional Amiga demo scene parlance, "greetings" are a way to express gratitude and admiration for other demo groups or for help they have contributed — this release has been helped very much by our testers and contributors:

* **Dimitris Panokostas** — author of [Amiberry](https://amiberry.com), who has done a *tremendous* job improving Amiga emulation scaling over the last two years, and has been extremely patient with our ranting about how Amiga scaling has been broken for 30 years. He has gone above and beyond to satisfy our nerdy requests to deliver an emulator that gets things right — and this will hopefully spread to other Amiga emulators in the future.
* **StatMat** — for adding music support and QR code manual support to the launcher, and fixing lots of edge case bugs.
* **AmigaBill** — for featuring us in a 2-hour livestream that let us go in-depth on the new scaling fixes, latency, emulators, accuracy and everything that's new in this release. If you are interested, you can [check it out here](https://www.twitch.tv/videos/2746470548?t=00h26m38s).
* **h0ffman** — for contributing his curated modern demo scene picks, and for assisting with 060 testing and insisting on adding PCMCIA mass storage support.
* **Desire *&* TTE** — for getting us a WHDLoad version of the winning demo of Revision 2026 hot off the presses! Literally hours before this release of AmigaVision! 😄
* **Sorgelig** — for continuing to update the MiSTer Amiga core.
* **robinsonb5** — for chipping away at any MiSTer core bugs and incompatibilities.


## 🛠️ Stay Updated *&* Help Us Make AmigaVision Even Better

If you find any bugs or settings that need improvements, file a ticket on the [AmigaVision] web site.

AmigaVision is an open source project, and we welcome contributions from the community.

You can follow us on [Bluesky], [Mastodon], [YouTube], [Twitch] or via [RSS], and updates will be posted when new releases happen.

**Enjoy the best of what the Amiga platform has to offer!**

[AmigaVision]:https://amiga.vision
[Mastodon]:https://mastodon.social/@amiga_vision
[Bluesky]:https://bsky.app/profile/amiga.vision
[YouTube]:https://youtube.com/@amiga_vision
[Twitch]:https://twitch.tv/amiga_vision
[RSS]:https://amiga.vision/feed.xml
