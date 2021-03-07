# AGSImager

## dependencies
- python3
- [pipenv](https://pipenv.readthedocs.io)

## setup environment
- `make env`

## prerequisites
- A bootable HDF to use as base (FFS formatted, all files are copied to DH0: of the output image)
- WHDLoad archives (LhA compressed) in `TITLES_DIR/game` and `TITLES_DIR/demo` (all subdirectories are scanned)

## operation
- `make index`
  - index WHDLoad archives in the `TITLES_DIR` path
- `make image`
  - create the Amiga HDF image and filesystem specified in `configs/MegaAGS.yaml`
- `make screenshots`
  - create scaled IFF images from arbitrary PNG files placed in `screenshots` 
- `make sqlite`
  - create sqlite database from `data/db/titles.csv` (for easier viewing and editing)
