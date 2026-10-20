#!/usr/bin/env python3
"""Select a fresh build cache and remove obsolete default generations.

Run between builds. Named caches (including ECS and comparison runs) and
incremental image baselines are independent and are preserved.
"""

import argparse
from datetime import datetime
from pathlib import Path
import re
import shutil


def invalidate(root):
    root.mkdir(parents=True, exist_ok=True)
    generation = datetime.now().strftime("%Y%m%d%H%M%S%f")
    marker = root / "build-cache-generation.txt"
    temporary_marker = marker.with_suffix(".tmp")
    temporary_marker.write_text(generation + "\n", encoding="utf-8")
    temporary_marker.replace(marker)
    print(f"Build cache generation bumped to {generation}", flush=True)
    build = root / "build"
    if not build.exists():
        return
    for entry in sorted(build.iterdir()):
        if entry.name == generation:
            continue
        if not re.fullmatch(r"(?:current|\d{14}|\d{20})(?:\.trash\.\d+)?", entry.name):
            continue
        if entry.is_symlink():
            entry.unlink()
        elif entry.is_dir():
            print(f"Removing obsolete build cache: {entry}", flush=True)
            shutil.rmtree(entry)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-root", type=Path,
                        default=Path.home() / "Library/Caches/AmigaVision")
    invalidate(parser.parse_args().cache_root)
