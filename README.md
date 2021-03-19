# AGSImager

## dependencies
- python@3.9
- [pipenv](https://pipenv.readthedocs.io)

## set up python environment
- `make env`

## prerequisites
- A bootable HDF to use as base (FFS formatted, all files are copied to DH0: of the output image) at `$AGSCONTENT/base/base.hdf`
- WHDLoad archives (LhA compressed) in `$AGSCONTENT/titles/game` and `$AGSCONTENT/titles/demo` (all subdirectories are scanned)

## operations

First have a look at the path variables in `.env` and edit if needed.

For full usage enter `pipenv shell` and use the following commands directly:

- `./ags_index.py --help`
  - content indexing tool
- `./ags_build.py --help`
  - image building tool
- `./ags_screenshot.py --help`
  - iff image conversion tool

Common usage is covered by makefile "shortuts":

- `make index`
  - index WHDLoad archives in the `$AGSCONTENT` path
- `make image`
  - create the Amiga HDF image and filesystem specified in `configs/MegaAGS.yaml`
- `make screenshots`
  - create scaled IFF images from arbitrary PNG files placed in `screenshots` 
- `make sqlite`
  - create sqlite database from `data/db/titles.csv` (for easier viewing and editing)
