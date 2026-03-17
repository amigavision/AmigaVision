# AmigaVision

Amiga HDF image builder using WHDL or custom installs, using the [Arcade Game Selector] launcher as a front-end.

## Dependencies

- Python 3.11
- `pipenv`
- ImageMagick
- `make`

The final step in the build process requires [FS-UAE](https://fs-uae.net) to copy all files to a PFS3-formatted HDF image. This is not an ideal setup, but as far as we know, no library exists that supports manipulation of PFS3 volumes without a bunch of dependencies (like C#). As a consequence the entire file tree to be copied first needs to be created on the host filesystem.

## Prerequisites
- A bootable HDF to use as base (FFS formatted, all files are copied to `DH0:` of the output image) at `$AGSCONTENT/base/base.hdf`
- WHDLoad archives (LhA compressed) in `$AGSCONTENT/titles/game` and `$AGSCONTENT/titles/demo` (all subdirectories are scanned)
- An [FS-UAE](https://fs-uae.net) 3.x binary at the path defined in `$FSUAEBIN`. 

## Set Up Python Environment
- `make env`

## Operations

First have a look at the path variables in `.env` and edit as needed.

Common usage is covered by makefile "shortcuts":

- `make index` — Index canonical WHDLoad archives in the `$AGSCONTENT` path, update database references, and write the resulting state back to `data/db/titles.csv`
- `make index-add-missing` — Run indexing, write the current SQLite state back to `data/db/titles.csv`, and then append or backfill missing fields in the CSV using an online Wikidata lookup.
- `make manifests` — Regenerate all archive manifests under `$AGSCONTENT/manifests`
- `make missing-manifests` — Generate manifests only for archives that do not already have one
- `make verify-manifests` — Verify `.lha` archive contents against the manifests in `$AGSCONTENT/manifests`
- `make sync-manifests` — Generate missing manifests and report stale manifests whose archive no longer exists
- `make sync-manifests-apply` — Generate missing manifests and remove stale manifests
- `make prune-manifests` — Report stale manifests without deleting them
- `make prune-manifests-apply` — Remove stale manifests whose archive no longer exists
- `make promote-newer-archives [SOURCE=...]` — Promote newer `.lha` archives from the `${AGSCONTENT}/titles/manual-downloads` directory into the canonical tree.
- `make missing-images` — Print how many titles still lack low-res screenshots.
- `make sync-images` — Preferred image pipeline. Import matching PNGs from `data/img_highres/Unprocessed/`, fetch missing demo screenshots from Demozoo, Pouet, and Exotica, fetch missing game screenshots from Lemon Amiga in Chrome and then itch.io, convert staged images into canonical low-res and high-res IFF screenshots, and print the remaining missing count.
- `make sync-images-interactive` — Alias for `make sync-images`.
- `make image` — Create the Amiga HDF image and filesystem specified in `configs/AmigaVision.yaml`
- `make pi` — Build `AmigaVision.hdf`, inject it and `replay/` payload into a RePlayOS base image, and output a 16GB flashable `.img`
- `make screenshots` — Create scaled IFF images from arbitrary PNG files placed in `screenshots` 
- `make sqlite` — Create SQLite database from `data/db/titles.csv` (for easier viewing and editing)
- `make csv` — Output the contents of SQLite database to `data/db/titles.csv` (for committing to version control)

Manifests are stored in a mirrored tree under `$AGSCONTENT/manifests`, not next to the `.lha` archives in `$AGSCONTENT/titles`.
Archive indexing and manifest generation ignore staging or non-canonical content under `retired/`, `manual-downloads/`, and `manual-downloads/imported/`.
`make index-add-missing` skips remote Wikidata re-lookups for game rows that already have a `hol_id` or `lemon_id`.
When `make index-add-missing` writes `title` and `title_short`, it only fills missing `title_short` values and leaves existing ones unchanged. Existing `country` values are also left untouched. New `title_short` values normalize trailing articles such as `Punisher, The`, always drop leading `The`, avoid mid-word truncation, prefer dropping subtitles or parenthetical suffixes before clipping, and strip filler words like `Disk` / `Disc` when that produces a cleaner fit.
Image staging uses `data/img_downloads/<id>/`. `make sync-images` first imports any matching source files from `data/img_highres/Unprocessed/` into staging, then fetches missing demo screenshots from Demozoo/Pouet and missing game screenshots from Lemon. You can also place your own images there and name them `1.png`, `2.png`, `3.png`, etc. to preserve screenshot order. `make sync-images` writes:
- low-res `data/img/<id>.iff` from screenshot `2` when present, otherwise screenshot `3`, otherwise the first staged screenshot
- high-res `data/img_highres/<id>-N.iff` for every staged screenshot number `N`
`make sync-images` is the normal path: it imports local backlog PNGs first, fetches demo screenshots from Demozoo and then Pouet when IDs exist, falls back to Exotica title search for unresolved demos, then tries Lemon Amiga for game rows with `lemon_id`, and finally uses itch.io title search for any remaining unresolved games before converting to IFF. Chrome also needs View > Developer > Allow JavaScript from Apple Events enabled so the script can read the page source afterward.

For full usage enter `pipenv shell` and use the following commands directly:

- `./build/ags_index.py --help` — Content indexing tool
- `./build/ags_imager.py --help` — Image building tool
- `./build/ags_screenshot.py --help` — IFF image conversion tool

[Arcade Game Selector]:https://github.com/MagerValp/ArcadeGameSelector
