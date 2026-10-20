# Game container inventory — 2026-10-20

Audited 4,270 game entries against local AV-Content archives and a fresh 5,693-file listing of the configured public WHDLoad archive source. Comparisons preserve language, chipset, memory, timing, and content-edition variants. Version comparisons use container filenames; embedded slave versions were inspected where present. This establishes currency against that source, not against every independently published WHDLoad patch.

## Updated selections

32 game entries updated. Existing game IDs, preferences, control options, and descriptive metadata are unchanged.

| Game | Previous | Current | Entries |
|---|---|---|---:|
| Academy: Tau Ceti II | v1.1 | v1.2 | 1 |
| Alien 3 | v2.1 | v2.2 | 1 |
| Armour-Geddon | v1.0 | v1.1 | 1 |
| Artificial Dreams | v1.0 | v1.1 | 1 |
| Battle Command | v1.2 | v2.0 | 1 |
| Black Dawn II | v1.1 | v1.2 | 1 |
| Captain Dynamo | v1.3 | v1.4 | 1 |
| Cybersphere Plus | v0.01 | v1.1 | 1 |
| Donkey Kong | v1.0 | v1.2 | 1 |
| Eye of the Beholder | v0.2 | v0.3 | 1 |
| Eye of the Beholder II: The Legend of Darkmoon | v0.1 | v0.3 | 1 |
| Flucht Aus Colditz | v1.2 | v1.4a | 1 |
| Highway Patrol II | v1.2 | v1.3 | 2 |
| Kick Off 2 | v1.09 | v1.09a | 5 |
| Kick Off 2: Competition Version | v1.09 | v1.09a | 1 |
| Kick Off 2: World Cup 1990 | v1.09 | v1.09a | 4 |
| Lure of the Temptress | v2.1 | v2.2 | 4 |
| Magic Pockets | v3.0 | v3.3 | 1 |
| OsWALD of the Ice Floes | v1.1 | v1.2 | 1 |
| Tapper | v0.1 | v1.0 | 1 |
| Ultima VI: The False Prophet | v1.1 | v1.2 | 1 |

## Remaining inventory

- 4,113 entries have no newer compatible container in the local/upstream inventory.
- 1 entry deliberately retains an older container: Shadow of the Beast v2.1B. The v2.6 rows document graphical glitches and point back to that fallback.
- 148 entries use unversioned archive names, so filename comparison cannot establish their currency.
- 8 entries have no archive selected. Every nonempty selected game archive exists locally.

## Cleanup

Deleted 112 superseded game archives (154,510,437 bytes, approximately 147 MiB), including retired and staging copies, plus 256 repository manifests and 2 AV-Content manifests. No selected container was deleted. Each removal had a newer same-variant container whose contents were read successfully and whose slave layout covered the older container.

Retained Emerald Mines CD v1.0 in retired/: its older engine supports saving progress/highscores, while the v2.0 readme explicitly says that support was removed. It is not an equivalent obsolete copy.

A second cleanup scan found no remaining safely superseded game archives or manifests under these rules. Distinct editions and unrelated demo archives were retained.

## Validation

- Read every member of all 32 replacement archives and verified their manifest hashes.
- Generated all 64 normal/quiet launch scripts for the updated entries.
- Confirmed only archive path, slave path, and version changed in the CSV.
- Seven archive comparison/exclusion/inventory tests passed.
- Fixed the greedy filename parser that misread Crystal Hammer V1/V2 editions as slave versions.
- No emulator gameplay test or full HDF rebuild was performed.

## Repeat the inventory

```sh
pipenv run python build/audit_game_versions.py \
  --titles-dir /Users/limi/Developer/AV-Content/titles \
  --upstream-list /tmp/av-current-upstream.txt \
  --report /tmp/game-container-inventory.json
```

The upstream list is the output of `mega-find / --pattern=*.lha` after opening the configured public source. The audit command is read-only except for its report.

<details>
<summary>Updated container selections (32 entries)</summary>

| Game | Selected container |
|---|---|
| Academy: Tau Ceti II | `game/Academy_v1.2_2943.lha` |
| Alien 3 | `game/Alien3_v2.2.lha` |
| Armour-Geddon | `game/ArmourGeddon_v1.1_NTSC.lha` |
| Artificial Dreams | `game/ArtificialDreams_v1.1_0493.lha` |
| Battle Command | `game/BattleCommand_v2.0_0858.lha` |
| Black Dawn II | `game/BlackDawn2_v1.2.lha` |
| Captain Dynamo | `game/Dynamo_v1.4_0995.lha` |
| Cybersphere Plus | `game/_generic/CyberspherePlus_v1.1.lha` |
| Donkey Kong | `game/DonkeyKong_v1.2.lha` |
| Eye of the Beholder | `game/_hacks/EyeOfTheBeholder_v0.3_AGA.lha` |
| Eye of the Beholder II: The Legend of Darkmoon | `game/_hacks/EyeOfTheBeholder2_v0.3_AGA.lha` |
| Flucht Aus Colditz | `game/FluchtAusColditz_v1.4a_De.lha` |
| Highway Patrol II | `game/HighwayPatrol2_v1.3_2305.lha` |
| Highway Patrol II | `game/HighwayPatrol2_v1.3_Fast_2305.lha` |
| Kick Off 2 | `game/KickOff2_v1.09a_2191.lha` |
| Kick Off 2 | `game/KickOff2_v1.09a_De_1245.lha` |
| Kick Off 2 | `game/KickOff2_v1.09a_Es_2507.lha` |
| Kick Off 2 | `game/KickOff2_v1.09a_Fr.lha` |
| Kick Off 2 | `game/KickOff2_v1.09a_It_2574.lha` |
| Kick Off 2: Competition Version | `game/KickOff2CompetitionVersion_v1.09a.lha` |
| Kick Off 2: World Cup 1990 | `game/KickOff2PlusWorldCup90_v1.09a_0168.lha` |
| Kick Off 2: World Cup 1990 | `game/KickOff2PlusWorldCup90_v1.09a_De_0689.lha` |
| Kick Off 2: World Cup 1990 | `game/KickOff2PlusWorldCup90_v1.09a_Fr.lha` |
| Kick Off 2: World Cup 1990 | `game/KickOff2PlusWorldCup90_v1.09a_It_2573.lha` |
| Lure of the Temptress | `game/LureOfTheTemptress_v2.2_2030.lha` |
| Lure of the Temptress | `game/LureOfTheTemptress_v2.2_De.lha` |
| Lure of the Temptress | `game/LureOfTheTemptress_v2.2_Fr_2040.lha` |
| Lure of the Temptress | `game/LureOfTheTemptress_v2.2_It_2028.lha` |
| Magic Pockets | `game/_hacks/MagicPockets_v3.3_NTSC.lha` |
| OsWALD of the Ice Floes | `game/Oswald_v1.2_NTSC.lha` |
| Tapper | `game/_generic/Tapper_v1.0.lha` |
| Ultima VI: The False Prophet | `game/Ultima6_v1.2_0294.lha` |

</details>
