#!/usr/bin/env python3

import re
import sys
from pathlib import Path
from user_paths import normalize_path


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: generate_listings.py <avs-root> <output-dir>")

    src = Path(sys.argv[1])
    # Prefer the complete hi-res launcher. Incremental preparation temporarily
    # preserves it outside DH1 and may leave only new entries in AVS-MedRes.
    if src.name in {"AVS", "AVS-MedRes"}:
        for candidate in (src.parent / "AVS", src.parent.parent / ".hires-launcher-cache", src.parent / "AVS-MedRes"):
            if (candidate / "By Title.avs").is_dir():
                src = candidate
                break
    dst = Path(normalize_path(sys.argv[2]))
    # Shared run scripts may be in the hi-res tree, including its preserved
    # location while an incremental workspace is being prepared.
    run_roots = [src]
    if src.name in {"AVS", "AVS-MedRes"}:
        run_roots.extend([src.parent / "AVS", src.parent.parent / ".hires-launcher-cache"])
    run_root = next((root for root in run_roots if (root / "Run/Demo").is_dir()), src)

    all_games_root = src / "By Title.avs"
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
        if not (run_root / relative).is_file():
            raise SystemExit(f"Missing game launch target: {relative}")
        game_names.add(relative.rsplit("/", 1)[1])
    game_names = sorted(game_names, key=str.casefold)

    run_demo_root = run_root / "Run" / "Demo"
    if not run_demo_root.is_dir():
        raise SystemExit(f"Missing demo run directory: {run_demo_root}")
    demo_names = sorted((path.name for path in run_demo_root.iterdir()
                         if path.is_file() and not path.name.endswith(".uaem")), key=str.casefold)
    # Validate both inputs before replacing any existing release listings.
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "games.txt").write_text("\n".join(game_names), encoding="latin-1", errors="replace")
    (dst / "demos.txt").write_text("\n".join(demo_names), encoding="latin-1", errors="replace")


if __name__ == "__main__":
    main()
