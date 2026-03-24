#!/usr/bin/env python3

import argparse
import os
import sys

FSCHR_FORBIDDEN = [":"]

FSCHR_AMIGA_TO_UAE = {
    "\"": "%22",
    "*": "%2a",
    "<": "%3c",
    ">": "%3e",
    "?": "%3f",
    "|": "%7e",
}

FSCHR_AMIGA_TO_UAE_LAST = {
    " ": "%20",
    ".": "%2e",
}


def convert_filename_a2uae(name: str) -> str:
    if len(name) < 1:
        return name
    for char in FSCHR_FORBIDDEN:
        name = name.replace(char, "")
    name = name.replace("%", "%25")
    for char, escaped in FSCHR_AMIGA_TO_UAE.items():
        name = name.replace(char, escaped)
    for char, escaped in FSCHR_AMIGA_TO_UAE_LAST.items():
        if name[-1] == char:
            name = name[:-1] + escaped
    return name


def sanitize_tree(root: str, verbose: bool = False) -> int:
    renamed = 0
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        for name in dirnames + filenames:
            src_path = os.path.join(dirpath, name)
            if os.path.islink(src_path):
                continue

            sanitized = convert_filename_a2uae(name)
            if sanitized == name:
                continue

            dst_path = os.path.join(dirpath, sanitized)
            if os.path.exists(dst_path):
                raise FileExistsError("sanitized path already exists: {}".format(dst_path))

            os.rename(src_path, dst_path)
            renamed += 1
            if verbose:
                print("{} -> {}".format(src_path, dst_path))
    return renamed


def main() -> int:
    parser = argparse.ArgumentParser(description="Rewrite a tree using UAE-safe host filenames.")
    parser.add_argument("root", help="Root directory to sanitize")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    if not os.path.isdir(args.root):
        print("error: directory not found: {}".format(args.root), file=sys.stderr)
        return 1

    renamed = sanitize_tree(args.root, verbose=args.verbose)
    print("Sanitized {} path(s) under {}".format(renamed, args.root))
    return 0


if __name__ == "__main__":
    sys.exit(main())
