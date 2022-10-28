# AGSImager

## dependencies
- python@3.9
- [pipenv](https://pipenv.readthedocs.io)
- imagemagick
- make

The final step in the build process requires [FS-UAE](https://fs-uae.net) to copy all files to a PFS3-formatted HDF image. This is not an ideal setup, but as far as I know there exists no library that supports manipulation of PFS3 volumes. A consequence is that the entire file tree to be copied first needs to be created on the host filesystem, which presents issues if that filesystem imposes file name restrictions that AmigaDOS/PFS3 doesn't. 

macOS/APFS supports any file name possible on Amiga and is, to my knowledge, the only system AGSImager has been tested on so far. 

## prerequisites
- A bootable HDF to use as base (FFS formatted, all files are copied to DH0: of the output image) at `$AGSCONTENT/base/base.hdf`
- WHDLoad archives (LhA compressed) in `$AGSCONTENT/titles/game` and `$AGSCONTENT/titles/demo` (all subdirectories are scanned)
- An [FS-UAE](https://fs-uae.net) 3.x binary at the path defined in `$FSUAEBIN`. 

## set up python environment
- `make env`

## operations

First have a look at the path variables in `.env` and edit as needed.

For full usage enter `pipenv shell` and use the following commands directly:

- `./ags_index.py --help`
  - content indexing tool
- `./ags_imager.py --help`
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
 