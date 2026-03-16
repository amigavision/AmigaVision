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
- `make image` — Create the Amiga HDF image and filesystem specified in `configs/AmigaVision.yaml`
- `make pi` — Build `AmigaVision.hdf`, inject it and `replay/` payload into a RePlayOS base image, and output a 16GB flashable `.img`
- `make screenshots` — Create scaled IFF images from arbitrary PNG files placed in `screenshots` 
- `make sqlite` — Create SQLite database from `data/db/titles.csv` (for easier viewing and editing)
- `make csv` — Output the contents of SQLite database to `data/db/titles.csv` (for committing to version control)

Manifests are stored in a mirrored tree under `$AGSCONTENT/manifests`, not next to the `.lha` archives in `$AGSCONTENT/titles`.
Archive indexing and manifest generation ignore staging or non-canonical content under `retired/`, `manual-downloads/`, `manual-downloads/imported/`, and `mega-downloads/`.

For full usage enter `pipenv shell` and use the following commands directly:

- `./build/ags_index.py --help` — Content indexing tool
- `./build/ags_imager.py --help` — Image building tool
- `./build/ags_screenshot.py --help` — IFF image conversion tool

[Arcade Game Selector]:https://github.com/MagerValp/ArcadeGameSelector
