# AGSImager

## Dependencies
- python3
- [pipenv](https://pipenv.readthedocs.io)

## Set up environment
- `make env`

## Prerequisites
- A bootable HDF to use as base (FFS formatted, all files are copied to DH0: of the output image)
- WHDLoad archives (LhA compressed) in `TITLES_DIR/game` and `TITLES_DIR/demo` (all subdirectories are scanned)

## Operations

Remember to execute these from within `pipenv shell`:

- `make index`
  - index WHDLoad archives in the `TITLES_DIR` path
- `make image`
  - create the Amiga HDF image and filesystem specified in `configs/MegaAGS.yaml` — note that this may segfault when mounting drives, just run the last commmand in the makefile again if it does
- `make screenshots`
  - create scaled IFF images from arbitrary PNG files placed in `screenshots` 
- `make sqlite`
  - create sqlite database from `data/db/titles.csv` (for easier viewing and editing)
