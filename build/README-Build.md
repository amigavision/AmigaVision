# AmigaVision

Amiga HDF image builder using WHDL or custom installs, using the [Arcade Game Selector] launcher as a front-end.

## Dependencies

- Python 3.11
- `pipenv`
- ImageMagick
- `make`

The final step in the build process uses [Amiberry](https://github.com/BlitterStudio/amiberry) by default to copy all files to a PFS3-formatted HDF image. This is not an ideal setup, but as far as we know, no library exists that supports manipulation of PFS3 volumes without a bunch of dependencies (like C#). As a consequence the entire file tree to be copied first needs to be created on the host filesystem.

## Prerequisites
- The AV-Base checkout alongside AmigaVision (or set `AGSBASE` to its location). Its root is the DH0 payload, including UAE `.uaem` metadata sidecars. Git files are excluded from staging; build layers replace the base startup files as usual.
- WHDLoad archives (LhA compressed) in `$AGSCONTENT/titles/game` and `$AGSCONTENT/titles/demo` (all subdirectories are scanned)
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
   Prompt for the release date, then package all platform-specific release artifacts from the built image.

## Title video modes

The `ntsc` field in `data/db/titles.csv` controls the title's video mode and pixel proportions:

| Value | Mode | Pixel proportions |
|---|---|---|
| `0` or blank | PAL, 50Hz | 16:15 at 4×; square pixels at 5× |
| `1` | NTSC, 60Hz | 5:6 at 5×, using the `ags-vadjust` `NTSC` correction |
| `2` | PAL60, 60Hz | Standard crop without `NTSC`; 16:15 at 4×, square pixels at 5× |

Both `1` and `2` select NTSC timing in generated launch scripts. The NTSC pixel-aspect correction applies at 5×; 6× retains the existing widescreen crop. The launcher metadata distinguishes NTSC from PAL60. The MiSTer Overscale toggle and Force PAL/NTSC options continue to override the generated crop or timing as before.

The field was migrated from the previous numbering: old `4` becomes `1`, old PAL60 `1` becomes `2`, and old World/standard NTSC `2`/`3` are consolidated into NTSC `1`. Use only `0`, `1`, or `2` for new entries.

## Other Useful Targets

If you only need a specific packaged output instead of the full release set, use:

- `make amiga`
  Package the real-Amiga hardware release artifact.
- `make emulators`
  Package the reusable Amiberry-based emulator distribution.
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

Builds use the root of the sibling `AV-Base` checkout by default. Set `AGSBASE`
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
make test-image AGSDEST=/tmp/av-native-test/output AGSTEMP=/tmp/av-native-test/stage
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

Main and ECS images are capped at **16,000,000,000 bytes (16 GB decimal)**,
rounded down to whole cylinders. DH0 receives its normal free-space reserve plus
**200,000,000 extra bytes (200 MB decimal)**. DH1 gets the rest of the image.
The Mini keeps its existing payload-sized allocation for FAT32 compatibility.

Once an image is built, its partition boundaries stay fixed during incremental
updates. Added files consume the existing free space; they do not resize DH0 or
DH1. If a partition no longer fits, a full rebuild can repartition within the same
16 GB cap. A payload that cannot fit that cap fails without replacing the working
image. Changes to the size cap, configuration profile, or PFS filesystem binary
also trigger a full rebuild. Shell-sensitive deletion paths that cannot be safely
represented in an AmigaDOS script fall back to a full rebuild.

To force a complete transactional rebuild:

```sh
make image IMAGE_CLONE_ARGS=--full
```

Direct `build/ags_imager.py` calls prepare a full image unless `--incremental` is passed;
with `--incremental`, image allocation is deferred until `clone-amiberry` runs.
Do not launch the generated config directly for an incremental workspace.

Planning and transaction regression tests:

```sh
pipenv run python build/test_ags_image_update.py
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
