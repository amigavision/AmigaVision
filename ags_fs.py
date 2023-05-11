#!/usr/bin/env python3

# AGSImager: Native filesystem functions

import os
import shutil
import subprocess
import sys
from ast import literal_eval as make_tuple

import ags_util as util

# -----------------------------------------------------------------------------

def is_amiga_devicename(name: str):
    return len(name) == 3 and name[0].isalpha() and name[1].isalpha() and name[2].isnumeric()

def extract_base_image(base_hdf: str, dest: str):
    tmp_dest = dest + "_unpack"
    _ = subprocess.run(["xdftool", base_hdf, "unpack", tmp_dest, "fsuae"])
    for f in os.listdir(tmp_dest):
        shutil.move(os.path.join(tmp_dest, f), dest)
    util.rm_path(tmp_dest)

def build_pfs(hdf_path, clone_path, verbose):
    FS_OVERHEAD = 1.06 # filesystem size fudge factor
    SECTOR_SIZE = 512 # fixed
    BLOCK_SIZE = 512 # amiga only support RDBs with a 512 byte block size

    if verbose:
        print("building PFS container...")

    pfs3_bin = util.path("data", "pfs3", "pfs3.bin")
    if not util.is_file(pfs3_bin):
        raise IOError("PFS3 filesystem doesn't exist: " + pfs3_bin)

    if verbose:
        print(" > calculating partition sizes...")

    num_buffers = 128
    heads = 4
    sectors = 63
    cylinder_size = SECTOR_SIZE * heads * sectors
    num_cyls_rdb = 1
    total_cyls = num_cyls_rdb

    partitions = [] # (partition name, cylinders)
    for f in sorted(os.listdir(clone_path)):
        if util.is_dir(util.path(clone_path, f)) and is_amiga_devicename(f):
            mb_free = 120 if f == "DH0" else 80
            cyls = int(FS_OVERHEAD * (util.get_dir_size(util.path(clone_path, f), BLOCK_SIZE) + (mb_free * 1024 * 1024))) // cylinder_size
            partitions.append(("DH" + str(len(partitions)), cyls))
            total_cyls += cyls

    if util.is_file(hdf_path):
        os.remove(hdf_path)

    if verbose: print(" > creating pfs container ({}MB)...".format((total_cyls * cylinder_size) // (1024 * 1024)))
    if verbose: print(" > drive geometry: {} cylinders, {} heads, {} sectors".format(total_cyls + 1, heads, sectors))
    r = subprocess.run([
        "rdbtool", hdf_path,
        "create",
        "chs={},{},{}".format(total_cyls + 1, heads, sectors),
        "+", "init",
        "rdb_cyls={}".format(num_cyls_rdb),
        "rdb_flags=0x2"
    ])

    if verbose: print(" > adding filesystem...")
    r = subprocess.run([
        "rdbtool", hdf_path,
        "fsadd", pfs3_bin,
        "fs=PFS3"
    ], stdout=subprocess.PIPE)

    if verbose:
        print(" > adding partitions...")

    # add boot partition
    part = partitions.pop(0)
    if verbose: print("    > " + part[0])
    r = subprocess.run([
        "rdbtool", hdf_path,
        "add", "name={}".format(part[0]),
        "start={}".format(num_cyls_rdb),
        "size={}".format(part[1]),
        "fs=PFS3",
        "bs={}".format(BLOCK_SIZE),
        "max_transfer=0x0001FE00",
        "mask=0x7FFFFFFE",
        "num_buffer={}".format(num_buffers),
        "bootable=True",
        "pri=1"
    ], stdout=subprocess.PIPE)

    # add subsequent partitions
    for part in partitions:
        if verbose: print("    > " + part[0])
        r = subprocess.run(["rdbtool", hdf_path, "free"], stdout=subprocess.PIPE, universal_newlines=True)
        free = make_tuple(r.stdout.splitlines()[0])
        free_start = int(free[0])
        free_end = int(free[1])
        part_start = free_start
        part_end = part_start + part[1]
        if part_end > free_end:
            part_end = free_end
        r = subprocess.run([
            "rdbtool", hdf_path,
            "add", "name={}".format(part[0]),
            "start={}".format(part_start),
            "end={}".format(part_end),
            "fs=PFS3",
            "bs={}".format(BLOCK_SIZE),
            "max_transfer=0x0001FE00",
            "mask=0x7FFFFFFE",
            "num_buffer={}".format(num_buffers)
        ], stdout=subprocess.PIPE)
    return

# -----------------------------------------------------------------------------
# replace characters forbidden on some filesystems to format UAE will translate

FSCHR_FORBIDDEN = [":"]

FSCHR_AMIGA_TO_UAE = {
    "\"": "%22",
    "*": "%2a",
    "<": "%3c",
    ">": "%3e",
    "?": "%3f",
    "|": "%7e"
}

FSCHR_AMIGA_TO_UAE_LAST = {
    " ": "%20",
    ".": "%2e"
}

def convert_filename_a2uae(n):
    if len(n) < 1:
        return n
    for char in FSCHR_FORBIDDEN:
        n = n.replace(char, "")
    n = n.replace("%", "%25")
    for char, escaped in FSCHR_AMIGA_TO_UAE.items():
        n = n.replace(char, escaped)
    for char, escaped in FSCHR_AMIGA_TO_UAE_LAST.items():
        if n[-1] == char:
            n = n[:-1] + escaped
    return n

def convert_filename_uae2a(n):
    if len(n) < 1:
        return n
    n = n.replace("%25", "%")
    for char, escaped in FSCHR_AMIGA_TO_UAE.items():
        n = n.replace(escaped, char)
    for char, escaped in FSCHR_AMIGA_TO_UAE_LAST.items():
        n = n.replace(escaped, char)
    return n

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("not runnable")
    sys.exit(1)
