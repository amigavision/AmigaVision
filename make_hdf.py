#!/usr/bin/env python3

import sys
import os
import argparse
import subprocess
from ast import literal_eval as make_tuple
from functools import reduce

def is_file(path):
    return os.path.isfile(path)

def is_dir(path):
    return os.path.isdir(path)

def make_pfs(path, partitions, sectors, heads, bootable, verbose):
    MAX_HEADS = 16
    MAX_SECTORS = 255
    MAX_CYLINDERS = 65536
    BLOCK_SIZE = 512
    PFS3_BIN = "data/pfs3/pfs3.bin"

    if heads > MAX_HEADS:
        raise IOError("head count ({}) exceed maximum allowed ({})".format(heads, MAX_HEADS))
    if sectors > MAX_SECTORS:
        raise IOError("sector count ({}) exceed maximum allowed ({})".format(sectors, MAX_SECTORS))

    if not is_file(PFS3_BIN):
        raise IOError("PFS3 filesystem doesn't exist: " + PFS3_BIN)
    if is_file(path):
        raise IOError("out_hdf file already exists")

    cylinder_size = BLOCK_SIZE * heads * sectors

    partitions = list(map(lambda p: (p[0], int(1024 * 1024 * p[1]) // cylinder_size), partitions))
    num_cyls_dsk = reduce(lambda acc, p: acc + p[1], partitions, 0)
    num_cyls_rdb = 1
    total_cyls = num_cyls_rdb + num_cyls_dsk

    if total_cyls > MAX_CYLINDERS:
        raise IOError("total cylinders ({}) exceed maximum allowed ({})".format(total_cyls, MAX_CYLINDERS))

    if verbose:
        print("building PFS container...")

    if verbose: print(" > creating pfs container ({}MB)...".format((total_cyls * cylinder_size) // (1024 * 1024)))
    r = subprocess.run(["rdbtool", path,
                        "create", "chs={},{},{}".format(total_cyls + 1, heads, sectors), "+", "init", "rdb_cyls={}".format(num_cyls_rdb)])

    if verbose: print(" > adding filesystem...")
    r = subprocess.run(["rdbtool", path, "fsadd", PFS3_BIN, "fs=PFS3"], stdout=subprocess.PIPE)

    if verbose:
        print(" > adding partitions...")

    # add boot partition
    part = partitions.pop(0)
    if verbose: print("    > " + part[0])
    r = subprocess.run(["rdbtool", path,
                        "add", "name={}".format(part[0]),
                        "start={}".format(num_cyls_rdb), "size={}".format(part[1]),
                        "fs=PFS3", "block_size={}".format(BLOCK_SIZE), "max_transfer=0x0001FE00", "mask=0x7FFFFFFE",
                        "num_buffer=300", "bootable={}".format("True" if bootable else "False")], stdout=subprocess.PIPE)

    # add subsequent partitions
    for part in partitions:
        if verbose: print("    > " + part[0])
        r = subprocess.run(["rdbtool", path, "free"], stdout=subprocess.PIPE, universal_newlines=True)
        free = make_tuple(r.stdout.splitlines()[0])
        free_start = int(free[0])
        free_end = int(free[1])
        part_start = free_start
        part_end = part_start + part[1]
        if part_end > free_end:
            part_end = free_end
        r = subprocess.run(["rdbtool", path,
                            "add", "name={}".format(part[0]),
                            "start={}".format(part_start), "end={}".format(part_end),
                            "fs=PFS3", "block_size={}".format(BLOCK_SIZE), "max_transfer=0x0001FE00",
                            "mask=0x7FFFFFFE", "num_buffer=300"], stdout=subprocess.PIPE)
    return

# -----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--out_hdf", dest="out_hdf", metavar="FILE", help="output HDF")
    parser.add_argument("-p", "--partition", dest="partitions", action="append", help="add partition::size (example 'DH0::120')")
    parser.add_argument("-b", "--bootable", dest="bootable", action="store_true", default=False, help="make bootable (false)")
    parser.add_argument("--sectors", dest="sectors", type=int, default=63, help="set sector count (63)")
    parser.add_argument("--heads", dest="heads", type=int, default=4, help="set head count (4)")
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", default=False, help="verbose output")

    try:
        args = parser.parse_args()
        if not args.out_hdf:
            raise IOError("out_hdf argument missing")
        if not args.partitions:
            raise IOError("no partitions defined")

        partitions = [] # (name, size)
        for p in args.partitions:
            d = p.split("::")
            if len(d) == 2:
                if int(d[1]) > 0:
                    partitions.append((""+d[0], int(d[1])))
        if len(partitions) < 1:
            raise IOError("no valid partitions defined")

        make_pfs(args.out_hdf, partitions, args.sectors, args.heads, args.bootable, args.verbose)

    # except Exception as err:
    except IOError as err:
        print("error - {}".format(err))
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
