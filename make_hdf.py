#!/usr/bin/env python3

import sys
import os
import argparse
import subprocess
from ast import literal_eval as make_tuple

def is_file(path):
    return os.path.isfile(path)

def is_dir(path):
    return os.path.isdir(path)

def make_pfs(path, size, verbose):
    if verbose:
        print("building PFS container...")

    if is_file(path):
        raise IOError("out_hdf file already exists")

    pfs3_bin = "data/pfs3/pfs3.bin"
    if not is_file(pfs3_bin):
        raise IOError("PFS3 filesystem doesn't exist: " + pfs3_bin)

    block_size = 512
    heads = 4
    sectors = 63
    cylinder_size = block_size * heads * sectors

    num_cyls_rdb = 1
    num_cyls_dsk = int(1024 * 1024 * size) // cylinder_size
    total_cyls = num_cyls_rdb + num_cyls_dsk

    if verbose:
        print(" > creating pfs container...")
    r = subprocess.run(["rdbtool", path, "create", "chs={},{},{}".format(total_cyls, heads, sectors), "+", "init", "rdb_cyls={}".format(num_cyls_rdb)])

    if verbose:
        print(" > adding filesystem...")
    r = subprocess.run(["rdbtool", path, "fsadd", pfs3_bin, "fs=PFS3"], stdout=subprocess.PIPE)

    if verbose:
        print(" > adding partition...")

    r = subprocess.run(["rdbtool", path, "free"], stdout=subprocess.PIPE, universal_newlines=True)

    free = make_tuple(r.stdout.splitlines()[0])
    start_cyl = int(free[0])
    end_cyl = int(free[1])
    r = subprocess.run(["rdbtool", path,
                        "add", "start={}".format(start_cyl), "end={}".format(end_cyl),
                        "fs=PFS3", "block_size={}".format(block_size), "max_transfer=0x0001FE00",
                        "mask=0x7FFFFFFE", "num_buffer=300"], stdout=subprocess.PIPE)
    return

# -----------------------------------------------------------------------------

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--out_hdf", dest="out_hdf", metavar="FILE", help="output HDF")
    parser.add_argument("-s", "--size", dest="size", type=int, default=128, help="size (in megabytes)")
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", default=False, help="verbose output")

    try:
        args = parser.parse_args()

        if not args.out_hdf:
            raise IOError("out_hdf argument missing")

        make_pfs(args.out_hdf, args.size, args.verbose)

    # except Exception as err:
    except IOError as err:
        print("error - {}".format(err))
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
