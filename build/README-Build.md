# AmigaVision

Amiga HDF image builder using WHDL or custom installs, using the AVS launcher as a front-end.

## Dependencies

- Python 3.11
- `pipenv`
- ImageMagick
- `make`

The final step in the build process uses [Amiberry](https://github.com/BlitterStudio/amiberry) by default to copy all files to a PFS3-formatted HDF image. This is not an ideal setup, but as far as we know, no library exists that supports manipulation of PFS3 volumes without a bunch of dependencies (like C#). As a consequence the entire file tree to be copied first needs to be created on the host filesystem.

## Prerequisites
- The AV-Base checkout alongside AmigaVision (or set `AVSBASE` to its location). Its root is the DH0 payload, including UAE `.uaem` metadata sidecars. Git files are excluded from staging; build layers replace the base startup files as usual.
- WHDLoad archives (LhA compressed) in `$AVSCONTENT/titles/game` and `$AVSCONTENT/titles/demo` (all subdirectories are scanned)
- An [Amiberry](https://github.com/BlitterStudio/amiberry) binary at the path defined in `$AMIBERRYBIN`.

## Standard Release Flow

Copy `.env.example` to `.env`, then edit the path variables in `.env` as needed.

The normal end-to-end release process is:

1. `make env`
   Set up the Python environment used by the build tools.
2. `make update`
   Pull archives from the configured source, promote newer manual-downloads archives into the canonical tree, re-index the content database, and run the preferred image sync pipeline.
3. `make image`
   Create the main `AmigaVision.hdf` image using the standard Amiberry-based clone process.
4. `make distros`
   Prompt once for the release version (default: today's date) and output directory, then package the supported platform releases without further prompts. Mini building and packaging are temporarily excluded until its image is optimized for the 4 GB target again; use `make mini-image` and `make mini` separately when needed. Reuse existing main and ECS images from their configured locations, or from a previous distro run's `.build/images` directory. Build each missing image automatically using `image` or `ecs-image`. Existing images are reused regardless of age; run those targets explicitly when you want fresh images. Press Enter at either prompt to keep its default. The selected directory holds finished packages and a temporary `.build` subdirectory for generated images, listings, caches, and working files, so a large external drive can handle the whole run. This workspace is removed when the run exits, including on failure.

Full distro runs always create the emulator 7z archive. The optional archive choice and `EMULATORS_ARCHIVE` setting apply only to standalone `make emulators` runs. Noninteractive runs use `DISTRO_DATE` and `DISTRO_OUT` directly.

Full distro runs also build PiStorm AGA (PiStorm32 Lite, from the main HDF) and PiStorm ECS (classic PiStorm, from the ECS HDF). Both use `PISTORM_ROM` and `AMIBERRYBIN` and write dated `.img.xz` files to the selected output directory. Full runs share downloads and the compiled converter in a temporary run-local cache.

Both real Amiga archives are included: `AmigaVision-Amiga-<date>.img.xz` from the main HDF and `AmigaVision-Amiga-ECS-<date>.img.xz` from the ECS HDF, with SHA-256 and MD5 checksum files.

Amiga/ECS compression defaults to xz preset 1. Use `make distros AMIGA_XZ_PRESET=6` to restore the previous compression setting, or choose any preset from 0 to 9. PiStorm and RPi continue to use preset 1. The format remains `.img.xz` for all disk-image releases.

Full distro runs package in this order: Amiga, RPi, PiStorm AGA, Amiga ECS,
PiStorm ECS, MiSTer, Emulators, then CD32. The large temporary RPi/PiStorm
images are created and removed before the other release archives accumulate;
each required Amiga xz seed is still built before its consumers. This reduces
peak storage pressure while preserving compressed-block reuse.
At preset 1, SHA-256 hashes of each 3 MiB HDF block are recorded while those
exact bytes are supplied to xz. The small manifests live only in the run's
temporary workspace and are removed on exit. RPi and PiStorm reuse matching
compressed blocks directly from these finished archives without decompressing
the seed. Changed HDF blocks and other image data are compressed normally.
Each assembled output remains one standard XZ stream with CRC64 checks.

RPi looks up `roms/commodore_ami/AmigaVision.hdf` in the detached image's exFAT
directory and preserves every byte before and after that file. Unsupported or
fragmented layouts, missing/stale manifests, and incompatible seeds use ordinary
compression instead. Standalone targets likewise use ordinary compression when
no seed was generated in the current run. Preset overrides other than 1 retain
their previous compression behavior and do not generate reuse manifests.

Both reused RPi and PiStorm outputs are fully decompressed before publication;
their byte counts and SHA-256 hashes must match the complete intended image.
Corrupt compressed data, verification failures, disk errors, or input changes
abort the package and preserve any existing archive. Verification is retained
for PiStorm and newly applies to the RPi reuse path. Use `make distros XZ_REUSE=0`
to compare against ordinary compression.

For a smaller shared-seed test, run
`make distros DISTRO_PACKAGES=pi,pistorm-aga`. This builds the Amiga seed once,
then packages only RPi and PiStorm AGA; it skips ECS, MiSTer, Emulators, CD32,
and listings. If seed creation fails, the selected dependent packages are
skipped rather than spending time on ordinary-compression fallbacks.

Progress appears every 15 seconds during seed compression, reuse assembly,
and verification. Timings report seed compression with hashes, file-location
lookup, assembly, verification, reused/changed block counts, and zero decoded
seed bytes. Check these stages separately when comparing runs; package order
has changed and destination-drive conditions can affect timings.

Each platform has a dedicated output directory, such as `AmigaVision-Amiga-ECS/`, containing its dated archive and adjacent `.sha256.txt` and `.md5.txt` files. The same layout applies to individual packaging targets. Uncompressed emulator releases live under `AmigaVision-Emulators/` in their dated release folder.

MiSTer templates live in `content/distro_mister/`; external MiSTer payloads live in `$AVSCONTENT/distro_mister/`. Packaging combines those sources with the main HDF and generated listings, rather than copying miscellaneous build outputs. Emulator templates remain in `content/distro_emulators/`, with the external Visuals payload in `$AVSCONTENT/distro_emulators/Amiberry/Visuals/`. MiSTer sources no longer contain emulator Visuals or UAE launcher configurations.

`make pi` discovers a `RePlayOS*.img.zst` blank base in `REPLAYOS_BASE_IMG` (a file or directory). Fast zstd level 1 is used for the blank at rest: its mostly empty filesystem compresses well and unpacks quickly. Raw `.img` and gzip-compressed bases are also accepted. The prepared blank's `replay` filesystem must already fit the HDF plus at least 100 MiB of free space after copying support files; increasing only the raw container size does not resize that filesystem. The enlarged AmigaVision base has a 16.25 GiB replay partition and a 22.37 GB raw size, requiring a 32 GB or larger card.

Pi packaging unpacks a temporary image on the selected output storage, mounts and populates its replay partition, unmounts and detaches it, then writes `AmigaVision-RPi-<date>.img.xz` with multithreaded xz at preset 1, matching the existing release compression. The temporary raw image is removed after compression, including on failure, and the compressed blank base remains unchanged for the next run. Allow room on the output storage for both the raw working image and the compressed release. Pi releases receive the usual SHA-256 and MD5 checksum files.

Packaging stages payloads and writes compressed artifacts on the selected output storage. Compressor scratch files use its `.build/tmp` directory, including an explicit 7z working-directory setting. This also applies when packaging an individual distribution. CD32 ZIP staging and emulator installer staging use the output storage as well. Each platform’s `.build` directory is removed after its packaging step, on success or failure; finished artifacts and checksum files remain.

Full runs compress the main and saves HDFs once into independent 7z blocks at level 3. Each platform compresses only its smaller support files. The assembler writes the shared compressed blocks, platform blocks, and combined metadata directly into each final archive in one pass, without copying and repeatedly updating a large archive. It preserves filenames, CRCs, permissions, and timestamps; its inputs must use the non-solid, plain-header layout generated by these scripts. This shared seed is created lazily when MiSTer starts, after the disk-image builds have finished, and deleted after Emulators finishes.

PiStorm generates a small MBR/FAT boot prefix and streams it, the patched HDF, and partition padding into xz. It no longer writes a second full raw SD image. The prefix's partition layout and every FAT boot file are validated first. Before publication, the compressed result is independently decompressed and its complete byte count and SHA-256 are compared with the supplied image bytes. Existing releases remain intact if assembly or verification fails.

PiStorm compression reports input supplied, compressed output size, and elapsed time every 15 seconds, including while xz finishes buffered work. Input reaching 100% means all image bytes have been supplied; compression can still be running. Verification reports bytes checked separately.

Stage timing messages distinguish shared compression, platform-file compression, single-pass archive assembly, PiStorm prefix creation/streaming/verification, and checksums. RPi reports unpacking, attachment, mounting, support/BIOS copying, HDF copying, metadata cleanup, flushing, unmounting, and detachment separately.

For full-file compression measurements without retaining extra large archives, run the following with the images closed:

```sh
pipenv run python build/benchmark_xz_presets.py \
  "$HOME/Developer/AV-Output/AmigaVision.hdf" \
  "$HOME/Developer/AV-Output/AmigaVision-ECS.hdf" \
  --presets 1 3 --report /tmp/amigavision-xz-benchmark.json
```

The benchmark counts compressed output bytes and discards them; results exclude output-drive writes. Each completed measurement is saved immediately. A source change during a measurement is rejected.

See [the 2026-10-31 measurements](benchmark-results-2026-10-31.md) for the default-preset comparison and its limits.

Mini builds default to full rebuilds with `--no-build-cache`: menu trees and archives are built directly in the workspace without reading or saving reusable build trees. After success, the separate temporary workspace, any older Mini build cache, and retained image-update data are removed. The finished Mini image remains available for packaging and reuse. For repeated development builds, use `make mini-image MINI_INCREMENTAL=1` to enable and retain the build and image-update caches.

## Title video modes

The `ntsc` field in `data/db/titles.csv` controls the title's video mode and pixel proportions:

| Value | Mode | Pixel proportions |
|---|---|---|
| `0` or blank | PAL, 50Hz | 16:15 at 4×; square pixels at 5× |
| `1` | NTSC, 60Hz | 5:6 at 5×, using the `avs-vadjust` `NTSC` correction |
| `2` | PAL60, 60Hz | Standard crop without `NTSC`; 16:15 at 4×, square pixels at 5× |

Both `1` and `2` select NTSC timing in generated launch scripts. The NTSC pixel-aspect correction applies at 5×; 6× retains the existing widescreen crop. The launcher metadata distinguishes NTSC from PAL60. The MiSTer Overscale toggle and Force PAL/NTSC options continue to override the generated crop or timing as before.

The field was migrated from the previous numbering: old `4` becomes `1`, old PAL60 `1` becomes `2`, and old World/standard NTSC `2`/`3` are consolidated into NTSC `1`. Use only `0`, `1`, or `2` for new entries.

## Screenshot artwork

The current AGA launcher uses a 404×280 screenshot canvas at (236, 3).
Do not use the older 360×288 AGA size: its extra rows overlap the frame below
the screenshot. Fit the entire source with preserved aspect ratio and black
padding; native arcade pixels can be centered without enlargement. Number
gameplay slides from `-3`, reserving `-1` for cover art and `-2` for a title screen.

Use at most 240 colors, reserving indices 240–255 for the launcher. Color zero
must be black because the bitmap's word-aligned padding is also displayed.
Encode high-resolution artwork with ByteRun1 RLE. Validate decoded pixels,
reserved palette indices, and black padding; dimension checks alone do not catch
palette or padding conflicts.

ECS builds copy the checked-in `data/img_ecs` and `data/avs-ecs` artwork directly.
After changing AGA masters, run `make ecs-artwork` explicitly when those changes
should also update ECS. Conversion checksums live under
`$AVSCACHE_ROOT/ecs-artwork/` (default `~/Library/Caches/AmigaVision/ecs-artwork/`),
not in the repository. They only speed up conversion; image builds do not require
them. Deleting this local cache makes the next explicit conversion regenerate the
artwork. ECS preserves the canonical AGA 404×280 thumbnail geometry, using 13
graphics colors and three locked UI entries (cyan 13, black 14, white/Copper text 15). Its
4-bit RGB palette conversion lives in `ecs_artwork.py` and `ecs_palette.py`;
do not copy AGA bitmaps directly into the ECS launcher. The monochrome ECS
background remains separately maintained.

Standard artwork remains 320×128, prepared at 320×256 before half-height
resampling.

## Other Useful Targets

If you only need a specific packaged output instead of the full release set, use:

- `make amiga`
  Package the real-Amiga hardware release artifact.
- `make emulators`
  Package the reusable Amiberry, Copperline and WinUAE distribution, including
  the Windows installer checked into `content/distro_emulators`.
  Amiberry holds the canonical HDFs and ROM; Copperline uses the same assets.
  Copperline includes `configs/AmigaVision.toml` with relative media paths,
  while the UAE emulators include `Configurations/default.uae` and
  `Configurations/AmigaVision.uae`. Each emulator has an `INSTALL.txt`.
  The installer can keep the existing emulator startup config or install
  AmigaVision as the default, backing up replaced configs. Interactive
  runs ask whether to create the 7z archive (default: no). Press Enter to keep
  `AmigaVision-Emulators-<date>/Amiberry`, `Copperline` and `WinUAE` in the selected output
  directory. Use `make emulators EMULATORS_ARCHIVE=0` to skip compression without
  the archive prompt, or `EMULATORS_ARCHIVE=1` to create the archive without
  that prompt. Noninteractive runs also skip the archive by default.
  Existing uncompressed output folders are preserved; choose a different output
  directory or date when rebuilding.
  On macOS, packaging stages files using native copy-on-write clones when the
  source and staging directory are on the same supporting filesystem (APFS).
  Other filesystems and cross-volume copies fall back to independent full copies.
- `make mister`
  Package the MiSTer release artifact.
- `make cd32`
  Generate the CD32 SD/USB/NAS payloads and build the CD32 MiSTer release artifact.
- `make pi`
  Build the Raspberry Pi / RePlayOS `.img.xz` package from the configured compressed blank base image.

For all other targets and maintenance tasks, run:

- `make`

[Arcade Game Selector]:https://github.com/MagerValp/ArcadeGameSelector

## Native base source

Builds use the root of the sibling `AV-Base` checkout by default. Set `AVSBASE`
in `.env` or pass `--base-dir DIR` to use another checkout. Keep all `.uaem`
sidecars, `.info` icons, and escaped filenames unchanged. Git control files and
host bookkeeping are excluded from the staged Amiga volume.

Native source caching hashes file contents and metadata sidecars, rather than
host timestamps. Staging uses copy-on-write clones or independent copies, never
source hardlinks. Build layers can safely replace startup files in the staged
copy. The final image remains PFS3 and uses the existing Amiberry cloner.

Run `make test-image` for the smaller test build. To keep its files separate:

```sh
mkdir -p /tmp/av-native-test/output /tmp/av-native-test/stage
make test-image AVSDEST=/tmp/av-native-test/output AVSTEMP=/tmp/av-native-test/stage
```

For a legacy HDF comparison, override the source explicitly:
`BASE_IMAGE_ARGS='--base-hdf /path/to/base.hdf'`.
`build/compare_base_builds.py --base-hdf FILE --base-dir DIR --work-dir NEW_DIR`
prints an isolated preparation comparison plan; add `--run` to prepare both
sources. Amiberry and amitools use different metadata serialization and filename
escaping, so raw staging differences require interpretation. A PFS round trip
through Amiberry verified all 10,052 manually copied base files, protection flags,
and comments; timestamps were ignored. The rebuilt base also booted to Workbench.

## Incremental PFS image updates

Run `make invalidate-build-cache` between builds to select a fresh preparation
cache and delete obsolete default generations, including the legacy `current`
directory. Named ECS/comparison caches and incremental image baselines are
preserved. Use `make clean-temp` to remove the main and ECS staging workspaces.

`make image` (and the Amiberry Mini, ECS, and test image targets) now updates an
existing image when it has a matching successful-build manifest. Preparation
still stages the desired complete filesystem on the Mac. The final clone hashes
payload contents and compares protection flags and comments, ignoring timestamps.
It copies only added/changed files and directories and removes deleted paths.
If nothing changed, Amiberry is skipped entirely. Incremental preparation skips
partition-size scans and reuses the existing boundaries. Capacity checks use the
content manifest already collected for comparison; a full rebuild derives its
layout from that same manifest without another filesystem walk.

The manifest and build lock live under
`~/Library/Caches/AmigaVision/image-updates/<output-path-hash>/`, outside the
per-generation build caches. The output directory contains only the image.
Each output path has its own cache entry, even when image filenames match.
Existing adjacent manifests and lock files migrate automatically, preserving a
valid incremental baseline. Clearing this cache or moving the output image to a
new path requires one full build to establish a new baseline.

On APFS, the cache also keeps a clean copy-on-write `baseline.hdf`. Booting or
testing the public output does not invalidate this baseline: later builds apply
changes to the clean cached image and replace the output after success. The public Output HDF may also be deleted; it is recreated from the cached
baseline, with changes applied if needed. Runtime
writes are deliberately excluded from generated builds. With no payload changes,
a modified output is restored from the cached baseline without starting Amiberry.
Creating the baseline shares unchanged blocks; it does not copy or hash 16 GB.
Existing matching images are adopted automatically. If filesystem cloning is
unavailable, the builder retains signature-based reuse and cannot reuse an
externally modified image without a clean baseline. Metadata-only ctime changes
no longer trigger rebuilds.

Updates use a disposable copy-on-write image on APFS, with a normal copy fallback.
The public HDF is replaced only after the emulator confirms success and PFS has
had time to flush writes. Failed or interrupted clones preserve the previous
image and manifest. A lock prevents concurrent clones to the same output.

Main and ECS images are capped at **15,800,000,000 bytes (15.8 GB decimal)**,
rounded down to whole cylinders, leaving room for PiStorm boot partitions on
16 GB SD cards. DH0 receives its normal free-space reserve plus
**100,000,000 extra bytes (100 MB decimal)**. DH1 gets the rest of the image.
The Mini keeps its existing payload-sized allocation for FAT32 compatibility.

Once an image is built, its partition boundaries stay fixed during incremental
updates. Added files consume the existing free space; they do not resize DH0 or
DH1. If a partition no longer fits, a full rebuild can repartition within the same
15.8 GB cap. A payload that cannot fit that cap fails without replacing the working
image. Changes to the size cap, configuration profile, or PFS filesystem binary
also trigger a full rebuild. Shell-sensitive deletion paths that cannot be safely
represented in an AmigaDOS script fall back to a full rebuild.

To force a complete transactional rebuild:

```sh
make image IMAGE_CLONE_ARGS=--full
```

Direct `build/avs_imager.py` calls prepare a full image unless `--incremental` is passed;
with `--incremental`, image allocation is deferred until `clone-amiberry` runs.
Do not launch the generated config directly for an incremental workspace.

Planning and transaction regression tests:

```sh
pipenv run python build/test_avs_image_update.py
```

## Warm-build work reuse

Unchanged staged hi-res launchers are validated and retained in place. Cached
output is restored only when staging is missing or has changed; changed inputs
still rebuild the launcher cache. This preserves staged file identities between
warm builds instead of deleting and recreating the screenshot tree.

Incremental cloner setup skips full-payload progress-statistics scans because the
updater generates its own clone script. Legacy backends compute their summary
once and share it between both progress outputs. Finder cleanup for incremental
builds happens inside the payload comparison rather than a separate tree walk.

The image cache also stores `scan-cache.json`. File hashes are reused only when
device, inode, size, modification time, and change time all match. UAE sidecars
are checked independently, so protection/comment changes are still detected.
Every scan discovers additions and deletions. A missing or incompatible scan
cache triggers content reads; it does not invalidate the clean HDF baseline or
require a full disk clone. The first comparison populates this cache, and later
warm comparisons report how many file hashes were reused.

Run the cache invalidation and launcher reuse tests with:

```sh
pipenv run python -m unittest discover -s build -p 'test_*cache.py'
```

Missing-archive auditing checks each distinct archive path once. Menu aliases are
matched using the existing SQLite lookup rules against missing rows only, rather
than repeatedly searching the complete title database. The `audit missing
archives` timing row makes this verification visible even on cached builds.

## Launcher naming

The launcher uses `AVS:`, `AVS`, `AVSMenu`, `AVSHelper`, `AVS.conf`, and `.avs`
menu directories. Launcher assets live in `data/avs`, `data/avs-highres`, and
`data/avs-ecs`; Python build modules use the `avs_` prefix. Local environment
variables use `AVSCONTENT`, `AVSDEST`, `AVSTEMP`, `AVSBASE`, and `AVSCACHEGEN`.

Older AV-Base launcher commands, fonts, and scripts are renamed in the staged
copy. The original base checkout is preserved. MiSTer's core-owned `ags_boot`
and `ags_current` protocol filenames remain compatible with existing cores.

The bundled launcher executables use the new paths, menu extension, and helper
port name. Their names were patched in place with zero padding for shorter
strings, preserving executable sizes, hunk layout, and relocation offsets.

### Non-selectable menu dividers

Menus with `ordering: declared` follow YAML declaration order after expanding
`!include` files. Configured folders, entries and dividers appear first; generated
or layered entries not listed in the YAML follow in their existing sort order.
No per-entry ranks are needed. This setting applies only to that menu, so title
collections keep their existing alphabetical, release, or numbered ordering.
The main AmigaVision menu and its Demo Scene submenu enable this mode.

```yaml
- ordering: declared
- About:
    informational: true
    note: About this collection.
- Games:
    divider: true
- !include Lists/Games-HallOfFame.yaml
- Spacer after games:
    divider: true
    label: ""
- "Demo Scene":
  - ordering: declared
  - !include Lists/Demos.yaml
  - !include Lists/Demos-Curated.yaml
```

A menu item with `divider: true` produces a non-selectable row without a
directory, launch script, screenshot, or metadata panel. Labels render as
`Games` exactly as written; brackets are never added automatically. An optional
`label: ""` creates a completely blank row. Spacer names only identify their marker files. In declared-order menus, repeated
spacer names are supported because their positions distinguish the files. In
legacy menus, give repeated names distinct ranks. Labels must fit the
30-character menu width. Supported divider options are `divider`, `label`, and
`rank`. Legacy menus without `ordering: declared` still support explicit ranks;
in declared mode these ranks are assigned automatically from the YAML order.

### Literal directories and actions

Menu keys are the actual directory or script names. An empty list reserves a
folder's position and lets the generator or base layer populate it:

```yaml
- ordering: declared
- Favorites:
    favorites: true
- By Title: []
- By Year: []
- Non-English: []
- Demo Scene:
  - ordering: declared
  - !include Lists/Demos.yaml
- Options: []
- Random Game:
    file: true
- Exit to Workbench:
    exit: true
```

`By Title` is `By Title.avs` on disk, `Options` is `Options.avs`, and `Random Game`
uses `Random Game.run`. Folder labels can be shortened without changing their
literal target names:

```yaml
- Demos - By Year:
  - label: By Year
- Music Disks - By Year:
  - label: By Year
```

Both display “By Year”, while keeping separate directories and artwork.
The optional `label` is direct folder metadata, not a reference identifier.
`file: true` lists an existing `.run` script; a missing script is a build error.
Favorites uses its configured path in AVS.conf. Exit uses the launcher's existing
missing-run-file exit behavior. Explicit Favorites and Exit entries replace their
default automatic positions.

Small `.menuitem` files record these action types and their generated sort order
through cached builds. They contain only a type character; their filenames are
the literal menu names. The generated `.dir` uses ordinary `D`/`F` rows, `V` for
Favorites, and `S` for dividers. Labeled directories use an `A` row containing
the actual filename, a TAB, and its display label. A `.avs.label` sidecar carries
this metadata through cached builds. The launcher keeps the real name for paths
and artwork, and uses the label only for drawing and letter shortcuts.

The generator stores a small `.divider` marker file and emits an `S` row in the
menu's `.dir` cache. Blank rows contain a single space after `S`; a zero-length
label would leave the previous label unchanged in the Amiga E parser. This needs the updated AVSMenu binaries in all three profiles;
old binaries treat unknown prefixes as directories. Divider rows use the existing
font and Copper gradient. Navigation skips them in both directions, when paging,
when jumping by initial character, and when initializing/restoring selection.
Consecutive dividers and leading/trailing dividers are supported. A menu containing
only dividers has no highlighted or actionable row.

Hi-res navigation combines the saved skin and one-bit text mask directly into
the visible bitmap, writing each completed word without an intermediate clear
or full-color staging copy. Constant background planes are left untouched.
Selection text uses bitmap OR/clear blits, preserving pixels outside the glyph
mask. This keeps edge scrolling responsive without exposing a cleared list.

Medium-resolution and ECS navigation redraws compose the background, text and selection in a reusable
off-screen Chip RAM bitmap. A completed viewport is copied to the visible
RastPort without an extra frame wait; paging and scrolling no longer
expose the intermediate background restore. The buffer is seeded from the screen
only once; partial selection redraws copy only the dirty rows to the screen.
The buffer uses one screen-sized
bitmap, is freed before screen closure,
and falls back to native drawing if allocation fails.

`build/launcher/dividers.s` holds the 68000 wrappers and
`build/launcher/patch_dividers.py` appends them to the recognized launcher versions
without altering existing relocation records. The patcher requires vasm, validates
known input hashes and hook instructions, and leaves already patched binaries
unchanged. For example:

```sh
python3 build/launcher/patch_dividers.py data/avs-highres/AVSMenu \
  --assembler /path/to/vasmm68k_mot --output /tmp/AVSMenu
```

The committed binaries already include the patch; ordinary image builds do not
need vasm. Python integration checks are in `build/test_menu_dividers.py`. The
additional `build/launcher/test_dividers_68k.py` checks execute the wrappers with
machine68k and vasm; `AVS_TEST_MENU` can select any of the three binary paths.
