# AGSImager

## dependencies
- python3
- [pipenv](https://pipenv.readthedocs.io)

## setup environment
- `make env`

## prerequisities
- A bootable HDF to use ase base (FFS formatted, all files are copied to DH0: of the output image)
- WHDLoad archives (LhA compressed) in `data/whdl/game` and `data/whdl/demo` (all subdirectories are scanned)

## operation
- `make index`
  - index WHDLoad archives in the `data/whdl` path
- `pipenv image`
  - create the Amiga HDF image and filesystem 

## todo
- Better documentation ;)
