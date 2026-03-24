#!/usr/bin/env python3

# AGSImager: Paths

import os

import ags_util as util

# -----------------------------------------------------------------------------

def cache_root():
    return util.path(os.getenv("HOME"), "Library", "Caches", "AmigaVision")

def cache_generation_file():
    return util.path(cache_root(), "build-cache-generation.txt")

def cache_generation():
    generation = os.getenv("AGSCACHEGEN")
    if generation:
        return generation.strip()
    generation_file = cache_generation_file()
    if util.is_file(generation_file):
        with open(generation_file, "r", encoding="utf-8") as f:
            value = f.read().strip()
            if value:
                return value
    return "current"

def content():
    return util.path(os.getenv("AGSCONTENT"))

def titles():
    return util.path(content(), "titles")

def manifests():
    return util.path(content(), "manifests")

def tmp():
    return util.path(os.getenv("AGSTEMP"))

def cache():
    return util.path(cache_root(), "build", cache_generation())

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
