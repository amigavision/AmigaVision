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

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("not runnable")
    sys.exit(1)
