# AGSImager

## dependencies
- python3
- python2/pip2 (for amitools)
- pipenv (https://pipenv.readthedocs.io)

## setup
- pip2 install -e dependencies/amitools-0.1.0/
- pipenv install

## prerequisities
- A bootable HDF to use ase base (FFS formatted, all files are copied to DH0: of the output image)
- WHDLoad archives (LhA compressed) in `data/whdl/game` and `data/whdl/demo` (all subdirectories are scanned)

## operation
- pipenv shell
  - ./ags_index.py -v
  - ./ags_build.py --help

## todo
- better documentation ;)
