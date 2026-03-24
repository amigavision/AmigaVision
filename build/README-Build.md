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

## Standard Release Flow

Copy `.env.example` to `.env`, then edit the path variables in `.env` as needed.

The normal end-to-end release process is:

1. `make updates`
   Pull archives from the configured source, promote newer manual-downloads archives into the canonical tree, re-index the content database, and run the preferred image sync pipeline.
2. `make image`
   Create the main `AmigaVision.hdf` image using the standard FS-UAE-based clone process.
3. `make distros`
   Prompt for the release date, then package all platform-specific release artifacts from the built image.

For all other targets and maintenance tasks, run:

- `make`

[Arcade Game Selector]:https://github.com/MagerValp/ArcadeGameSelector
