# AGSImager

Amiga HDF image builder using WHDL or custom installs, using the [Arcade Game Selector] launcher as a front-end.

## Dependencies
- python@3.9
- [pipenv](https://pipenv.readthedocs.io)
- imagemagick
- make

The final step in the build process requires [FS-UAE](https://fs-uae.net) to copy all files to a PFS3-formatted HDF image. This is not an ideal setup, but as far as I know no library exists that supports manipulation of PFS3 volumes. As a consequence the entire file tree to be copied first needs to be created on the host filesystem.

## Prerequisites
- A bootable HDF to use as base (FFS formatted, all files are copied to DH0: of the output image) at `$AGSCONTENT/base/base.hdf`
- WHDLoad archives (LhA compressed) in `$AGSCONTENT/titles/game` and `$AGSCONTENT/titles/demo` (all subdirectories are scanned)
- An [FS-UAE](https://fs-uae.net) 3.x binary at the path defined in `$FSUAEBIN`. 

## Set Up Python Environment
- `make env`

## Operations

First have a look at the path variables in `.env` and edit as needed.

For full usage enter `pipenv shell` and use the following commands directly:

- `./ags_index.py --help`
  - Content indexing tool
- `./ags_imager.py --help`
  - Image building tool
- `./ags_screenshot.py --help`
  - IFF image conversion tool

Common usage is covered by makefile "shortcuts":

- `make index`
  - Index WHDLoad archives in the `$AGSCONTENT` path
- `make image`
  - Create the Amiga HDF image and filesystem specified in `configs/MegaAGS.yaml`
- `make screenshots`
  - Create scaled IFF images from arbitrary PNG files placed in `screenshots` 
- `make sqlite`
  - Create SQLite database from `data/db/titles.csv` (for easier viewing and editing)
- `make csv`
  - Output the contents of SQLite database to `data/db/titles.csv` (for committing to version control)

[Arcade Game Selector]:https://github.com/MagerValp/ArcadeGameSelector
