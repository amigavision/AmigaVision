#!/usr/bin/env python3

# AGSImager: Paths

import os
import sys
import ags_util as util

# -----------------------------------------------------------------------------

def content():
    return util.path(os.getenv("AGSCONTENT"))

def titles():
    return util.path(content(), "titles")

def tmp():
    return util.path(os.getenv("AGSTEMP"))

def verify():
    vars = ["AGSCONTENT", "AGSDEST", "AGSTEMP", "FSUAEBIN", "FSUAEROM"]
    for var in vars:
        if os.getenv(var) is None:
            raise IOError("missing {} environment variable - check .env!".format(var))
    if not util.is_dir(content()):
        raise IOError("AGSCONTENT is not a directory - check .env!")
    if not util.is_file(util.path(os.getenv("FSUAEBIN"))):
        raise IOError("FSUAEBIN is not a file - check .env!")
    if not util.is_file(util.path(os.getenv("FSUAEROM"))):
        raise IOError("FSUAEROM is not a file - check .env!")
    return True

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("not runnable")
    sys.exit(1)
