#!/usr/bin/env python3

import os
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: generate_listings.py <ags2-root> <output-dir>")

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    dst.mkdir(parents=True, exist_ok=True)
    for path in dst.glob("*.txt"):
        if path.is_file():
            path.unlink()

    all_games_root = src / "[ All Games - By Title ].ags"
    if not all_games_root.is_dir():
        raise SystemExit(f"Missing all-games tree: {all_games_root}")

    game_names = sorted(
        {
            path.stem
            for path in all_games_root.rglob("*.run")
            if path.is_file()
        },
        key=str.casefold,
    )
    (dst / "games.txt").write_text("\n".join(game_names), encoding="latin-1", errors="replace")

    run_demo_root = src / "Run" / "Demo"
    if not run_demo_root.is_dir():
        raise SystemExit(f"Missing demo run directory: {run_demo_root}")
    demo_names = sorted(os.listdir(run_demo_root), key=str.casefold)
    (dst / "demos.txt").write_text("\n".join(demo_names), encoding="latin-1", errors="replace")


if __name__ == "__main__":
    main()
