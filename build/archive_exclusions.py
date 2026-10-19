"""Explicit archive opt-outs, independent of redundant-version metadata."""
from fnmatch import fnmatchcase
from functools import lru_cache
from pathlib import Path

EXCLUSIONS_FILE = Path(__file__).resolve().parents[1] / 'data/db/excluded_archives.txt'


@lru_cache(maxsize=1)
def exclusion_patterns():
    return tuple(line.strip().casefold() for line in EXCLUSIONS_FILE.read_text().splitlines()
                 if line.strip() and not line.lstrip().startswith('#'))


def is_excluded_archive(path):
    name = Path(path).name.casefold()
    return any(fnmatchcase(name, pattern) for pattern in exclusion_patterns())
