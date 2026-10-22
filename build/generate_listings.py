#!/usr/bin/env python3

import re
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: generate_listings.py <avs-root> <output-dir>")

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    dst.mkdir(parents=True, exist_ok=True)
    for path in dst.glob("*.txt"):
        if path.is_file():
            path.unlink()

    all_games_root = src / "[ All Games - By Title ].avs"
    if not all_games_root.is_dir():
        raise SystemExit(f"Missing all-games tree: {all_games_root}")

    # Menu labels can be shortened or ranked. Export the canonical script name
    # from the target instead, including games routed through Run/Issues.
    game_names = set()
    for path in all_games_root.rglob("*.run"):
        if not path.is_file():
            continue
        script = path.read_text(encoding="latin-1")
        target = re.fullmatch(r'\s*execute "AVS:(Run/(?:Game|Issues)/[^"\r\n]+)"\s*', script, re.IGNORECASE)
        if target is None:
            raise SystemExit(f"Unrecognized game launch script: {path}")
        relative = target.group(1)
        if not (src / relative).is_file():
            raise SystemExit(f"Missing game launch target: {relative}")
        game_names.add(relative.rsplit("/", 1)[1])
    game_names = sorted(game_names, key=str.casefold)
    (dst / "games.txt").write_text("\n".join(game_names), encoding="latin-1", errors="replace")

    run_demo_root = src / "Run" / "Demo"
    if not run_demo_root.is_dir():
        raise SystemExit(f"Missing demo run directory: {run_demo_root}")
    demo_names = sorted((path.name for path in run_demo_root.iterdir()
                         if path.is_file() and not path.name.endswith(".uaem")), key=str.casefold)
    (dst / "demos.txt").write_text("\n".join(demo_names), encoding="latin-1", errors="replace")


if __name__ == "__main__":
    main()
