# Errata review — 2026-10-26

Reviewed the 21 items on the ERRATA tab of the supplied workbook. The workbook itself is unchanged.

## Changes

| Sheet row | Entry | Result |
|---:|---|---|
| 2 | ASCII Express 01 | Normalized ID to `mags-notwhdl--asciiexpress01`; moved archive, run script, manifest and artwork to matching paths; updated Mini menu reference. Category remains Demo / Disk Magazine, which is the project's diskmag convention. |
| 4 | Way Too Rude | Identical archive already has a populated Logicoma/Loonies entry. Filled the older row's metadata and marked it redundant with a redirect to that entry. |
| 5 | Impossible Possibility | Normalized game ID/archive paths to demo; filled Mystic credit, March 1995, Demo subtype and Pouët ID 3952. |
| 6 | Muscles | Normalized game ID/archive paths to demo; filled Impulse credit, 1996-08-30, Demo subtype and Demozoo ID 9765. |
| 7 | Pulse | Normalized game ID/archive paths to demo; filled Nerve Axis credit, 1997-08-10, Demo subtype and Demozoo ID 19189. |
| 8 | Planetary Void | Added release date 2024-01-20. |
| 9 | Eon | Older row uses the identical archive/slave as the populated TBL row. Copied identifying metadata, marked it redundant, and redirected it to the populated row. |
| 10 | Tactical Transmissions | Older row uses the identical archive/slave as the populated Pattern Syndicate row. Corrected metadata including Music Disk subtype, marked it redundant, and redirected it to that row. |
| 11–12 | Last Train to Danzig | Preferred the WHDLoad entry; marked the standalone entry redundant and redirected it. Marked the WHDLoad entry AGA/060 and documented the 68060/32 MB Fast RAM requirement. Updated 060, curated and widescreen lists to reference the WHDLoad entry explicitly. MiSTer incompatibility is expected. |
| 14 | Random Access Music | Re-encoded the two monochrome slides (-4, -5) as opaque eight-plane images without changing RGB pixels. |
| 17 | 5th Gear crack intro | Re-encoded all four monochrome slides (-3 through -6) in the same way. |
| 18 | Amaze Multi Demo | Re-encoded monochrome slide -3. |
| 19 | Animatunes | Re-encoded monochrome slide -3. |
| 20 | Aquarium | Re-encoded monochrome slide -5. |
| 21 | Bronx Megademo 2 | Re-encoded monochrome slide -5. |

## Already addressed

Rows 22–25 (Captured Dreams and Darkside, packed/decrunched entries): the packed versions are already redundant and prefer the newer decrunched containers. Commit [4699e72](https://github.com/amigavision/AmigaVision/commit/4699e72e8a6500d82ae7cea9fb9cfa2d3c6db5ea) supplies four new screenshots per preferred container. Per the user's instruction, these artwork issues were disregarded.

## Intentional behavior

Row 15, Seduction: this title is tagged NSFW. The build deliberately replaces its artwork with the NSFW placeholder and strips all numbered slides. The user confirmed that this protection should remain in place; this erratum is intentional and requires no change.

## Evidence

- [Impossible Possibility on Pouët](https://www.pouet.net/prod.php?which=3952): Mystic, March 1995, Demo.
- [Muscles on Demozoo](https://demozoo.org/productions/9765/): Impulse, 30 August 1996, Amiga AGA demo.
- [Pulse on Demozoo](https://demozoo.org/productions/19189/): Nerve Axis, 10 August 1997, Amiga AGA demo.
- [Planetary Void on Demozoo](https://demozoo.org/productions/336645/): 20 January 2024.
- [Last Train to Danzig on Pouët](https://www.pouet.net/prod.php?which=66492): 68060, 2 MB Chip and 32 MB Fast RAM requirements.

## Verification and limits

- Verified the four moved archives against their manifests; archive bytes were not altered.
- Generated normal and quiet launch scripts for all four normalized entries and confirmed the three WHDLoad demos now install/launch from the demo path.
- Verified the changed duplicate/preference targets and migration of artwork manifest keys.
- All ten repaired monochrome screenshots retain identical decoded RGB pixels. Updated their ECS copies and content hashes. This is an asset-compatibility workaround, not a confirmed launcher-source diagnosis.
- Six existing artwork/naming tests pass.
- No full image rebuild, demo playback or MiSTer display test was performed. The monochrome-image repairs need that display check.
- Follow-up: corrected both Manhattan Dealers preference links to the existing Operation: Cleanstreets NTSC entry (`game--operationcleanstreetsntsc--operationcleanstreetsntsc`).
