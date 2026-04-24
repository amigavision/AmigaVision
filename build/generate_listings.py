#!/usr/bin/env python3

import os
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: generate_listings.py <ags2-root> <output-dir>")

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    run_root = src / "Run"
    mapping = {"Game": "games.txt", "Demo": "demos.txt"}

    missing = [str(run_root / kind) for kind in mapping if not (run_root / kind).is_dir()]
    if missing:
        raise SystemExit("Missing listing source directories: " + ", ".join(missing))

    dst.mkdir(parents=True, exist_ok=True)
    for path in dst.glob("*.txt"):
        if path.is_file():
            path.unlink()

    for kind, filename in mapping.items():
        names = sorted(os.listdir(run_root / kind), key=str.casefold)
        (dst / filename).write_text("\n".join(names), encoding="latin-1", errors="replace")


if __name__ == "__main__":
    main()
