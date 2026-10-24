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
   Prompt once for the release version (default: today's date) and output directory, then build the Mini image and package all platform-specific releases without further prompts. Press Enter at either prompt to keep its default. The selected directory holds finished packages and a `.build` subdirectory for generated images, listings, caches, and temporary files, so a large external drive can handle the whole run. Existing main HDF and content sources are read from their configured locations.

Full distro runs keep the emulator folders by default. Use `make distros EMULATORS_ARCHIVE=1` to create their 7z archive without adding another prompt. Noninteractive runs use `DISTRO_DATE` and `DISTRO_OUT` directly.

## Title video modes

The `ntsc` field in `data/db/titles.csv` controls the title's video mode and pixel proportions:

| Value | Mode | Pixel proportions |
|---|---|---|
| `0` or blank | PAL, 50Hz | 16:15 at 4×; square pixels at 5× |
| `1` | NTSC, 60Hz | 5:6 at 5×, using the `avs-vadjust` `NTSC` correction |
| `2` | PAL60, 60Hz | Standard crop without `NTSC`; 16:15 at 4×, square pixels at 5× |

Both `1` and `2` select NTSC timing in generated launch scripts. The NTSC pixel-aspect correction applies at 5×; 6× retains the existing widescreen crop. The launcher metadata distinguishes NTSC from PAL60. The MiSTer Overscale toggle and Force PAL/NTSC options continue to override the generated crop or timing as before.

The field was migrated from the previous numbering: old `4` becomes `1`, old PAL60 `1` becomes `2`, and old World/standard NTSC `2`/`3` are consolidated into NTSC `1`. Use only `0`, `1`, or `2` for new entries.

## Other Useful Targets

If you only need a specific packaged output instead of the full release set, use:

- `make amiga`
  Package the real-Amiga hardware release artifact.
- `make emulators`
  Package the reusable Amiberry and WinUAE emulator distribution.
  The canonical Amiberry tree contains `Amiberry/HardDrives`; WinUAE uses the
  same disk images from that folder, avoiding duplicate HDF images. Copy it into the chosen
  emulator data folder during installation. Each emulator includes
  identical `Configurations/default.uae` and `Configurations/AmigaVision.uae`
  files and an `INSTALL.txt`. Users can install only `AmigaVision.uae` to keep
  their existing emulator default. Interactive
  runs ask whether to create the 7z archive (default: no). Press Enter to keep
  `AmigaVision-Emulators-<date>/Amiberry` and `WinUAE` in the selected output
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
  Build the Raspberry Pi / RePlayOS `.img.xz` package from the configured base image.

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
