#!/usr/bin/env python3

# AVSImager: Paths

import os

import avs_util as util

# -----------------------------------------------------------------------------

def env_path(name):
    value = os.getenv(name)
    if value is None:
        return None
    return value.strip().strip('"')

def cache_root():
    return env_path("AVSCACHE_ROOT") or util.path(env_path("HOME"), "Library", "Caches", "AmigaVision")

def cache_generation_file():
    return util.path(cache_root(), "build-cache-generation.txt")

def cache_generation():
    generation = os.getenv("AVSCACHEGEN")
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
    return util.path(env_path("AVSCONTENT"))

def base():
    """Versioned DH0 payload; default to the sibling AV-Base checkout."""
    return env_path("AVSBASE") or os.path.abspath(util.path(
        os.path.dirname(__file__), "..", "..", "AV-Base"))

def repo_content():
    return util.path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content")

def titles():
    return util.path(content(), "titles")

def tracked_titles():
    return util.path(repo_content(), "titles")

def manifests():
    return util.path(repo_content(), "manifests")

def tmp():
    return util.path(env_path("AVSTEMP"))

def cache():
    return util.path(cache_root(), "build", cache_generation())

def verify():
    vars = ["AVSCONTENT", "AVSDEST", "AVSTEMP", "KICKSTART_ROM"]
    for var in vars:
        if os.getenv(var) is None:
            raise IOError("missing {} environment variable - check .env!".format(var))
    if not util.is_dir(content()):
        raise IOError("AVSCONTENT is not a directory - check .env!")
    if not util.is_file(util.path(env_path("KICKSTART_ROM"))):
        raise IOError("KICKSTART_ROM is not a file - check .env!")
    return True
