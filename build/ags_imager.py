#!/usr/bin/env python3

# AGSImager

# Database fields:
#
# id: Unique title identifier
# title: Full title (displayed in info box)
# title_short: Short title (displayed in list), *used as identifier for favorites feature and SAM integration*
# redundant: Exclude in add_all operations
# preferred_version: Use this version instead if title is fuzzy matched (i.e. not using precise name in yaml config)
# hardware: Hardware the title was originally targeting (OCS, OCS/CD, OCS/CDTV, AGA, AGA/CD, AGA/CD32, etc)
# aga: Title is AGA only (1=true)
# ntsc: Video mode and pixel aspect ratio (blank defaults to PAL)
#   0 = PAL at 50Hz (16:15 PAR @ 4X, 1:1 PAR @ 5X)
#   1 = NTSC at 60Hz (5:6 PAR @ 5X; NTSC crop correction)
#   2 = PAL60 at 60Hz (16:15 PAR @ 4X, 1:1 PAR @ 5X)
# scale: Viewport integer scale factor at 1080p (PAL: 4-6, NTSC: 5-6)
# vshift: Viewport vertical shift (higher value -> screen is shifted up)
#   Expressible range (higher values allowed but have no effect):
#   NTSC-5X: -16 ... 9
#   NTSC-6X: -16 ... 45
#   PAL-4X:  -11 ... 5
#   PAL-5X:  -11 ... 59
#   PAL-6X:  -11 ... 95
# hshift: Viewport horizontal shift (super hires pixels, higher value -> screen is shifted left)
# killaga: Use killaga hack when invoking whdload (1=true)
# gamepad: Title supports more than one button (1=true)
# lightgun: Title supports light gun (1=true)
# note: Extra prose displayed in the centered info box (without a label)
# issues: Known problems, displayed alongside notes and hack information
# hack: Modification/port information, displayed without a label
# release_date: Release date (YYYY or YYYY-MM-DD)
# country: Country of origin (comma separated list)
# language: Languages supported (comma separated list)
# developer: Developer (comma separated list)
# publisher: Publisher (comma separated list)
# players: Display wording, e.g. "4 Players (2 Simultaneously)"
# slave_args: Extra arguments passed in whdl invokation
# slave_version: WHDL install version (set by ags_index)
# slave_path: Path to WHDL slave in archive (set by ags_index)
# archive_path: th to WHDL install archive (set by ags_index)
# category: Category/genre (only used for demo scene auto-lists at the moment)
# subcategory: Subcategory/genre (only used for demo scene auto-lists at the moment)
# hol_id: Hall of Light ID
# lemon_id: Lemon Amiga ID

import argparse
from av_base_tree import directory_fingerprint, stage_directory
from ags_image_update import prepare_plan, PLAN_NAME
import ast
import hashlib
import json
import os
import shutil
import stat as stat_module
import subprocess
import sys
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from contextlib import contextmanager
from time import perf_counter
from sqlite3 import Connection

import ags_paths as paths
import ags_util as util
from ags_fs import build_pfs, calculate_pfs_partitions, extract_base_image, convert_filename_uae2a, get_base_hdf_cache_dir
from ags_make import make_hires_tree, count_tree_entries, make_autoentries, make_runscripts, make_tree, reset_warning_state, update_progress, warn_missing_archive
from ags_nsfw import make_nsfw_option
from ags_make import report_missing_launcher_images
from ags_query import audit_missing_archive_entries, entry_is_notwhdl, get_amiga_whd_dir, get_archive_path, get_entry, get_missing_archive_entry, get_preferred_entry, get_whd_dir, sanitize_entry
from ags_strings import strings
from ags_types import EntryCollection
from datetime import datetime

# -----------------------------------------------------------------------------

@contextmanager
def timed_step(timings, label):
    start = perf_counter()
    try:
        yield
    finally:
        timings.append((label, perf_counter() - start))


def print_timing_summary(timings):
    if not timings:
        return
    total = sum(duration for _, duration in timings)
    print("Build timing summary:")
    for label, duration in timings:
        print("  {:<24} {:>8.2f}s".format(label, duration))
    print("  {:<24} {:>8.2f}s".format("total", total))

def print_collection_timing_summary(collection):
    if not getattr(collection, "timing", None):
        return
    print("AGS timing detail:")
    for label, duration in sorted(collection.timing.items()):
        print("  {:<24} {:>8.2f}s".format(label, duration))


def is_exclusion_key(key: str) -> bool:
    return key in {"Exclude", "_Exclude", "_exclude"}


def collect_excluded_titles(menu) -> set[str]:
    excluded = set()
    if not isinstance(menu, list):
        return excluded
    for item in menu:
        if isinstance(item, list):
            excluded.update(collect_excluded_titles(item))
            continue
        if not isinstance(item, dict):
            continue
        for key, value in item.items():
            if is_exclusion_key(key):
                if isinstance(value, list):
                    for row in value:
                        if isinstance(row, str):
                            excluded.add(row)
                continue
            if isinstance(value, list):
                excluded.update(collect_excluded_titles(value))
    return excluded


def resolve_excluded_entry_ids(db: Connection, excluded_names: set[str]) -> set[str]:
    excluded_ids = set()
    for name in excluded_names:
        entry, pref_entry = get_entry(db, name)
        if entry and entry.get("id"):
            excluded_ids.add(entry["id"].lower())
        if pref_entry and pref_entry.get("id"):
            excluded_ids.add(pref_entry["id"].lower())
    return excluded_ids


def menu_item_is_excluded(name: str, excluded_names: set[str], excluded_ids: set[str], db: Connection, cache: dict[str, bool]) -> bool:
    if name in excluded_names:
        return True
    cached = cache.get(name)
    if cached is not None:
        return cached
    entry, pref_entry = get_entry(db, name)
    entry_ids = set()
    if entry and entry.get("id"):
        entry_ids.add(entry["id"].lower())
    if pref_entry and pref_entry.get("id"):
        entry_ids.add(pref_entry["id"].lower())
    matched = bool(entry_ids & excluded_ids)
    cache[name] = matched
    return matched


def prune_excluded_titles(menu, excluded_names: set[str], db: Connection, excluded_ids: set[str], match_cache: dict[str, bool] | None = None):
    if not isinstance(menu, list):
        return menu
    if match_cache is None:
        match_cache = {}
    pruned = []
    for item in menu:
        if isinstance(item, str):
            if not menu_item_is_excluded(item, excluded_names, excluded_ids, db, match_cache):
                pruned.append(item)
            continue
        if isinstance(item, list):
            nested = prune_excluded_titles(item, excluded_names, db, excluded_ids, match_cache)
            if nested:
                pruned.append(nested)
            continue
        if not isinstance(item, dict):
            pruned.append(item)
            continue
        next_item = {}
        for key, value in item.items():
            if is_exclusion_key(key):
                continue
            if isinstance(value, dict):
                if menu_item_is_excluded(key, excluded_names, excluded_ids, db, match_cache):
                    continue
                next_item[key] = value
                continue
            if isinstance(value, list):
                nested = prune_excluded_titles(value, excluded_names, db, excluded_ids, match_cache)
                if nested or key in {"image", "note", "ordering", "rank", "hidden"}:
                    next_item[key] = nested
                continue
            next_item[key] = value
        if next_item:
            pruned.append(next_item)
    return pruned

# -----------------------------------------------------------------------------

def fingerprint_file(path: str) -> dict:
    stat = os.stat(path)
    return {
        "path": os.path.abspath(path),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }

def walk_tree_stats(path):
    """Read each entry's metadata once and reuse scandir's directory entries."""
    def visit(relative):
        try:
            with os.scandir(os.path.join(path, relative)) as scan:
                entries = [(entry.name, entry.stat(), entry.is_symlink()) for entry in scan]
        except FileNotFoundError:
            if not relative:
                return
            raise
        dirs = sorted((row for row in entries if stat_module.S_ISDIR(row[1].st_mode)), key=lambda row: row[0])
        files = sorted((row for row in entries if not stat_module.S_ISDIR(row[1].st_mode)), key=lambda row: row[0])
        yield relative, dirs, files
        for name, _, symlink in dirs:
            if not symlink:
                yield from visit(os.path.join(relative, name))
    yield from visit("")


def fingerprint_tree(path: str, workers=1) -> list[dict]:
    if workers > 1:
        return parallel_tree_inventory(path, workers)
    return [
        {"path": os.path.join(relative, name), "is_dir": stat_module.S_ISDIR(st.st_mode),
         "size": st.st_size, "mtime_ns": st.st_mtime_ns}
        for relative, dirs, files in walk_tree_stats(path)
        for name, st, _ in dirs + files
    ]


def ordered_inventory(rows):
    """Restore the legacy traversal order after a sparse update, in memory."""
    children = {}
    for row in rows:
        children.setdefault(os.path.dirname(row["path"]), []).append(row)
    def visit(parent):
        entries = children.get(parent, [])
        dirs = sorted((r for r in entries if r["is_dir"]), key=lambda r: r["path"])
        files = sorted((r for r in entries if not r["is_dir"]), key=lambda r: r["path"])
        yield from dirs
        yield from files
        for row in dirs:
            yield from visit(row["path"])
    return list(visit(""))


def parallel_tree_inventory(path, workers=4):
    """Overlap metadata I/O across directories, then restore stable ordering."""
    def scan(relative):
        rows, dirs = [], []
        try:
            with os.scandir(os.path.join(path, relative)) as entries:
                for entry in entries:
                    st = entry.stat()
                    is_dir = stat_module.S_ISDIR(st.st_mode)
                    name = os.path.join(relative, entry.name)
                    rows.append({"path": name, "is_dir": is_dir,
                                 "size": st.st_size, "mtime_ns": st.st_mtime_ns})
                    if is_dir and not entry.is_symlink():
                        dirs.append(name)
        except FileNotFoundError:
            if relative:
                raise
        return rows, dirs
    rows = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending = {pool.submit(scan, "")}
        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                records, dirs = future.result()
                rows.extend(records)
                pending.update(pool.submit(scan, name) for name in dirs)
    return ordered_inventory(rows)


def hires_inventory_fingerprint(rows):
    return hash_payload([
        {"path": row["path"], "is_dir": True} if row["is_dir"] else row
        for row in rows if os.path.basename(row["path"]) != ".DS_Store"
    ])

def hash_payload(payload) -> str:
    return hashlib.sha1(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

def launcher_content_fingerprint(path: str, file_hashes=None) -> str:
    """Ignore rewritten timestamps while detecting every launcher input change."""
    digest = hashlib.sha1()
    previous = dict(file_hashes or {})
    if file_hashes is not None:
        file_hashes.clear()
    for relative_root, dirs, files in walk_tree_stats(path):
        digest.update(json.dumps([relative_root or ".", [row[0] for row in dirs]]).encode("utf-8"))
        for name, stat, _ in files:
            if name == ".DS_Store":
                continue
            relative = os.path.join(relative_root, name)
            full_path = os.path.join(path, relative)
            signature = [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns]
            cached = previous.get(relative)
            if cached and cached[:-1] == signature:
                content_hash = cached[-1]
            else:
                file_digest = hashlib.sha1()
                with open(full_path, "rb") as source:
                    for block in iter(lambda: source.read(1024 * 1024), b""):
                        file_digest.update(block)
                content_hash = file_digest.hexdigest()
            if file_hashes is not None:
                file_hashes[relative] = signature + [content_hash]
            digest.update(json.dumps([name, content_hash]).encode("utf-8"))
    return digest.hexdigest()

def build_or_reuse_hires_launcher(ags_path, hires_path, collection, workspace_state, append_delta=None, source_trees=None):
    # Full builds replace DH0. Keep the reusable tree beside it, not inside it.
    cache_path = util.path(os.path.dirname(os.path.dirname(hires_path)), ".hires-launcher-cache")
    manifest_path = cache_path + ".json"
    try:
        with open(manifest_path, encoding="utf-8") as source:
            manifest = json.load(source)
    except (OSError, ValueError):
        manifest = {}
    file_hashes = dict(manifest.get("medium_file_hashes", {}))
    previous_hashes = dict(file_hashes)
    medium_fingerprint = launcher_content_fingerprint(ags_path, file_hashes)
    hires_basis = {
        "assets": [source_trees[root] if source_trees is not None and root in source_trees else fingerprint_tree(root)
                   for root in ("data/ags2-highres", "data/img_highres")],
        "behavior": fingerprint_python_defs("build/ags_make.py", ["make_hires_tree", "make_hires_artwork"]),
        "encoder": [fingerprint_file("build/repair_hires_palettes.py"), fingerprint_file("build/iff_ilbm.py")],
    }
    cache_key = hash_payload({"medium_tree": medium_fingerprint,
                              "image_entries": collection.image_entries, **hires_basis})
    # New title artwork may be added, but changed encoder/rendering behavior
    # always requires replacing the entire hi-res output.
    rendering_basis = {k: v for k, v in hires_basis.items() if k != "assets"}
    staged_rows = (fingerprint_tree(hires_path, workers=4)
                   if util.is_dir(hires_path) and (manifest.get("key") == cache_key or append_delta is not None)
                   else None)
    staged_output = hires_inventory_fingerprint(staged_rows) if staged_rows is not None else None
    if (append_delta is not None and manifest.get("key") != cache_key and manifest.get("output") == staged_output
            and manifest.get("rendering_basis") == rendering_basis and util.is_dir(hires_path)):
        changed = [name for name, value in file_hashes.items()
                   if previous_hashes.get(name, [None])[-1] != value[-1]]
        # The append path cannot remove files. Unexpected changes use the normal
        # complete rebuild, including deletions introduced by a layer.
        if previous_hashes.keys() <= file_hashes.keys():
            with tempfile.TemporaryDirectory(prefix="hires-append-", dir=os.path.dirname(hires_path)) as temporary:
                medium = Path(temporary, "medium")
                medium.mkdir()
                for name in changed:
                    target = medium / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(Path(ags_path, name), target)
                output = Path(temporary, "hires")
                sparse_collection = EntryCollection()
                changed_names = set(changed)
                suffixes = [".iff", "-QR.iff"] + [f"-{i}.iff" for i in range(1, 10)]
                sparse_collection.image_entries = {
                    name: entry_id for name, entry_id in collection.image_entries.items()
                    if name in append_delta.image_entries or any(name + suffix in changed_names for suffix in suffixes)
                }
                make_hires_tree(str(medium), str(output), sparse_collection)
                # Invalidate first so interrupted merges cannot be reused.
                Path(manifest_path).unlink(missing_ok=True)
                # copytree uses copy2, preserving the known source file mtimes.
                # Update only this sparse inventory instead of rescanning DH1.
                updated = {row["path"]: row for row in staged_rows}
                updated.update({row["path"]: row for row in fingerprint_tree(str(output))})
                util.copytree(str(output), hires_path)
                staged_rows = ordered_inventory(updated.values())
            staged_output = hires_inventory_fingerprint(staged_rows)
            manifest = {"key": cache_key, "output": staged_output}
            print(" > Appended hi-res title files and updated directory indexes")
    staged_valid = (manifest.get("key") == cache_key and util.is_dir(hires_path)
                    and manifest.get("output") == staged_output)
    if staged_valid:
        print(" > Reusing staged hi-res launcher tree")
    else:
        cached_rows = fingerprint_tree(cache_path, workers=4) if manifest.get("key") == cache_key and util.is_dir(cache_path) else None
        if cached_rows is not None and manifest.get("output") == hires_inventory_fingerprint(cached_rows):
            print(" > Restoring cached hi-res launcher tree")
        else:
            print(" > Building hi-res launcher cache")
            if os.path.exists(manifest_path):
                os.remove(manifest_path)
            make_hires_tree(ags_path, cache_path, collection)
            cached_rows = fingerprint_tree(cache_path, workers=4)
            manifest = {"key": cache_key, "output": hires_inventory_fingerprint(cached_rows)}
        util.rm_path(hires_path)
        restore_hires_tree(cache_path, hires_path)
        staged_rows = cached_rows
    report_missing_launcher_images(
        ags_path, hires_path, collection,
        medium_files=file_hashes,
        hires_files=(row["path"] for row in staged_rows if not row["is_dir"]))
    manifest["rendering_basis"] = rendering_basis
    manifest["medium_file_hashes"] = file_hashes
    temporary = manifest_path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as destination:
        json.dump(manifest, destination)
    os.replace(temporary, manifest_path)
    workspace_state["hires_cache_key"] = cache_key
    workspace_state["hires_output_fingerprint"] = manifest["output"]

def restore_hires_tree(cache_path, hires_path):
    """Use APFS copy-on-write clones rather than copying gigabytes of pixels."""
    start = perf_counter()
    if sys.platform == "darwin":
        result = subprocess.run(["/bin/cp", "-cpR", cache_path, hires_path], capture_output=True, text=True)
        if result.returncode == 0:
            print(f" > Cloned hi-res tree in {perf_counter() - start:.2f}s")
            return
        # Other volumes may not support cloning. Discard any partial restore.
        util.rm_path(hires_path)
        print(" > Filesystem cloning unavailable; copying hi-res tree")
    util.copytree(cache_path, hires_path)
    print(f" > Copied hi-res tree in {perf_counter() - start:.2f}s")

def hires_output_fingerprint(path):
    """Validate generated files without rereading all screenshot pixel data."""
    return hires_inventory_fingerprint(fingerprint_tree(path, workers=4))

def fingerprint_python_defs(path: str, names: list[str]) -> str:
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    lines = source.splitlines()
    tree = ast.parse(source, filename=path)
    wanted = set(names)
    found = []
    for node in tree.body:
        node_name = getattr(node, "name", None)
        if node_name in wanted and hasattr(node, "lineno") and hasattr(node, "end_lineno"):
            segment = "\n".join(lines[node.lineno - 1:node.end_lineno])
            found.append((node_name, segment))
            continue
        if isinstance(node, ast.Assign):
            target_names = [target.id for target in node.targets if isinstance(target, ast.Name)]
            for target_name in target_names:
                if target_name in wanted and hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                    segment = "\n".join(lines[node.lineno - 1:node.end_lineno])
                    found.append((target_name, segment))
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name = node.target.id
            if target_name in wanted and hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                segment = "\n".join(lines[node.lineno - 1:node.end_lineno])
                found.append((target_name, segment))
    found.sort(key=lambda item: item[0])
    return hash_payload({
        "path": path,
        "defs": found,
        "missing": sorted(wanted - {name for name, _ in found}),
    })

AGS2_TREE_BEHAVIOR_FINGERPRINT = hash_payload([
    "launcher-on-DH1-v1",
    fingerprint_file('build/ags_ecs.py'),
    fingerprint_file('configs/ecs-preferred-versions.json'),
    fingerprint_python_defs("build/ags_make.py", ["make_tree", "make_entries", "make_entry", "make_autoentries", "make_runscripts", "make_runscript", "AGS_INFO_WIDTH", "AGS_INFO_HEIGHT", "make_note", "metadata_system", "metadata_blocks", "metadata_date", "metadata_wrap", "balanced_wrap", "wrap_note"]),
    fingerprint_python_defs("build/ags_query.py", ["get_entry", "get_missing_archive_entry", "get_missing_archive_entry_by_id", "get_preferred_entry", "name_is_fuzzy", "get_runscript_paths", "get_amiga_whd_dir", "get_whd_slavename", "entry_is_notwhdl"]),
    fingerprint_python_defs("build/ags_compositor.py", ["compose", "out_iff"]),
])

ARCHIVE_TREE_BEHAVIOR_FINGERPRINT = hash_payload([
    fingerprint_python_defs("build/ags_imager.py", ["get_archive_extract_cache_dir", "get_unique_archive_entries", "extract_entry", "extract_entries"]),
    fingerprint_python_defs("build/ags_query.py", ["get_archive_path", "get_amiga_whd_dir", "entry_is_notwhdl"]),
])

PFS_PARTITION_BEHAVIOR_FINGERPRINT = hash_payload([
    "launcher-on-DH1-v1",
    fingerprint_python_defs("build/ags_fs.py", ["get_pfs_free_mb", "calculate_pfs_partitions", "build_pfs"]),
    fingerprint_python_defs("build/ags_util.py", ["get_dir_size"]),
])

AUTOENTRIES_BEHAVIOR_FINGERPRINT = hash_payload([
    fingerprint_python_defs("build/ags_make.py", ["make_autoentries", "make_entry", "make_image", "wrap_note", "AGS_INFO_WIDTH", "AGS_INFO_HEIGHT", "make_note", "metadata_system", "metadata_blocks", "metadata_date", "metadata_wrap", "balanced_wrap"]),
    fingerprint_python_defs("build/ags_query.py", ["has_english_language", "get_languages", "get_publishers", "get_countries"]),
    fingerprint_python_defs("build/ags_strings.py", ["strings"]),
    fingerprint_python_defs("build/ags_compositor.py", ["compose", "out_iff"]),
])

def get_ags2_tree_cache_state(menu, db_path: str, base_ags2: str, runscript_template_path: str, config_file: str, args) -> dict:
    return {
        "menu": hash_payload(menu),
        "db": hash_payload(fingerprint_file(db_path)),
        "base_ags2": hash_payload(fingerprint_tree(base_ags2)),
        "runscript_template": hash_payload(fingerprint_file(runscript_template_path)),
        "args": hash_payload({
            "all_games": bool(args.all_games),
            "all_demos": bool(args.all_demos),
            "all_demoscene": bool(args.all_demoscene),
            "auto_lists": bool(args.auto_lists),
            "chipset_profile": getattr(args, "chipset_profile", "any"),
            "ecs_workspace": paths.tmp() if getattr(args, "chipset_profile", "any") == "ecs" else None,
        }),
        "behavior": AGS2_TREE_BEHAVIOR_FINGERPRINT,
    }

def append_input_state(db, cache_state, source_trees=None):
    """Keep row identities independently of the SQLite container's mtime."""
    assets = {}
    for root in ("data/img", "data/img_highres", "data/ags2-highres"):
        rows = []
        for relative, dirs, files in walk_tree_stats(root):
            for name, st, _ in dirs + files:
                path = os.path.join(relative, name)
                rows.append({"path": path, "is_dir": stat_module.S_ISDIR(st.st_mode),
                             "size": st.st_size, "mtime_ns": st.st_mtime_ns})
            for name, st, _ in files:
                assets[os.path.join(root, relative, name)] = [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns]
        if source_trees is not None and root != "data/img":
            source_trees[root] = rows
    return {
        "inputs": {"append_version": 1, **{k: v for k, v in cache_state.items() if k != "db"}},
        "rows": {row["id"]: hash_payload(dict(row)) for row in db.execute("SELECT * FROM titles")},
        "archive_inputs": {row["id"]: fingerprint_file(util.path(paths.titles(), row["archive_path"]))
                           if row["archive_path"] and util.is_file(util.path(paths.titles(), row["archive_path"])) else None
                           for row in db.execute("SELECT id, archive_path FROM titles")},
        "preferences": [row[0].strip().lower() for row in db.execute("SELECT preferred_version FROM titles WHERE preferred_version IS NOT NULL")],
        "assets": assets,
    }


def append_only_ids(previous, current, menu):
    """Reject changes that could alter an existing title or curated lookup."""
    if not previous or previous.get("inputs") != current["inputs"]:
        return None
    if any(current["rows"].get(k) != v for k, v in previous["rows"].items()):
        return None
    if any(current["archive_inputs"].get(k) != v for k, v in previous.get("archive_inputs", {}).items()):
        return None
    if any(current["assets"].get(k) != v for k, v in previous["assets"].items()):
        return None
    added = set(current["rows"]) - set(previous["rows"])
    if added.intersection(previous.get("preferences", [])):
        return None
    for path in set(current["assets"]) - set(previous["assets"]):
        stem = Path(path).stem.lower()
        if not any(stem == i.lower() or stem.startswith(i.lower() + "-") for i in added):
            return None
    # Use SQLite LIKE itself, including its wildcard/case rules. Checking only
    # the added IDs avoids repeating thousands of searches over the full DB.
    from sqlite3 import connect
    from ags_query import get_entry_lookup_patterns
    with connect(":memory:") as lookup:
        lookup.execute("CREATE TABLE additions (id TEXT)")
        lookup.executemany("INSERT INTO additions VALUES (?)", [(i,) for i in added])
        for name in iter_requested_menu_names(menu):
            for pattern in [name.lower()] + get_entry_lookup_patterns(name.lower()):
                if lookup.execute("SELECT 1 FROM additions WHERE id LIKE ? LIMIT 1", (pattern,)).fetchone():
                    return None
    return added


def merge_new_tree(source, destination, reject_runs=False):
    """Preflight before any writes; Amiga names are case insensitive."""
    files = [p for p in Path(source).rglob("*") if p.is_file()]
    directories = {}
    for p in files:
        target = Path(destination) / p.relative_to(source)
        if reject_runs and (p.suffix == ".run" or p.relative_to(source).parts[0] in {"Run", "RunQuiet"}):
            parent = target.parent
            if parent not in directories:
                directories[parent] = {n.name.casefold() for n in parent.iterdir()} if parent.is_dir() else set()
            if target.name.casefold() in directories[parent]:
                return False
    util.copytree(str(source), str(destination))
    return True


def try_append_launcher(db, args, menu, previous, current, clone_path, ags_path,
                        collection, runscript_template, workspace_state):
    if args.chipset_profile != "any" or not util.is_dir(ags_path):
        return None
    added = append_only_ids(previous, current, menu)
    if added is None or not restore_workspace_ags2_collection_snapshot(clone_path, collection):
        return None
    selected = EntryCollection()
    if args.all_games:
        add_all(db, selected, "Game")
    if args.all_demos:
        add_all(db, selected, "Demo", exclude_subcategories=["Disk Magazine", "Slide Show"])
    if args.all_demoscene:
        add_all(db, selected, "Demo")
    # Sanitation/preferred resolution must leave every existing auto entry intact.
    if any(i not in collection.by_id and i not in added for i in selected.by_id):
        return None
    delta = EntryCollection()
    delta.by_id = {i: e for i, e in selected.by_id.items() if i not in collection.by_id}
    with tempfile.TemporaryDirectory(prefix="ags-append-", dir=clone_path) as temporary:
        medium = util.path(temporary, "medium")
        util.make_dir(medium)
        if args.all_games or args.all_demos or args.all_demoscene or args.auto_lists:
            make_autoentries(delta, medium, games=args.all_games | args.auto_lists,
                             demos=args.all_demos | args.all_demoscene | args.auto_lists)
        make_runscripts(delta, medium, template=runscript_template)
        # Persist invalidation before touching the reusable tree. An interruption
        # must force a full rebuild, never reuse a partially appended workspace.
        workspace_state.pop("append_inputs", None)
        workspace_state.pop("ags2_cache_key", None)
        save_workspace_state(clone_path, workspace_state)
        if not merge_new_tree(medium, ags_path, reject_runs=True):
            return None
        snapshot_path = util.path(temporary, "collection.json")
        save_collection_snapshot(snapshot_path, delta)
        with open(snapshot_path) as source:
            snapshot = relativize_collection_snapshot(json.load(source), medium)
        merge_collection_snapshot(snapshot, collection, ags_path)
    print(" > Appended {} selected title(s); preserved existing launcher entries".format(len(delta.by_id)))
    return delta


def get_ags2_tree_cache_key(cache_state: dict) -> str:
    return hash_payload(cache_state)

def get_ags2_tree_state_path() -> str:
    return util.path(paths.cache(), "ags2-tree", "last-run.json")

def get_workspace_state_path(clone_path: str) -> str:
    return util.path(clone_path, ".workspace-state.json")

def get_workspace_ags2_collection_path(clone_path: str) -> str:
    return util.path(clone_path, ".workspace-ags2-collection.json")

def load_workspace_state(clone_path: str) -> dict:
    state_path = get_workspace_state_path(clone_path)
    if not util.is_file(state_path):
        return {}
    with open(state_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_workspace_state(clone_path: str, state: dict) -> None:
    state_path = get_workspace_state_path(clone_path)
    util.make_dir(os.path.dirname(state_path))
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, sort_keys=True, separators=(",", ":"))

def restore_workspace_ags2_collection_snapshot(clone_path: str, collection: EntryCollection) -> bool:
    snapshot_path = get_workspace_ags2_collection_path(clone_path)
    if not util.is_file(snapshot_path):
        return False
    load_collection_snapshot(snapshot_path, collection)
    return True

def save_workspace_ags2_collection_snapshot(clone_path: str, collection: EntryCollection) -> None:
    save_collection_snapshot(get_workspace_ags2_collection_path(clone_path), collection)

def report_ags2_tree_cache_miss(cache_state: dict) -> None:
    state_path = get_ags2_tree_state_path()
    if not util.is_file(state_path):
        print(" > AGS2 Cache Miss: no prior cache state")
        return
    with open(state_path, "r", encoding="utf-8") as f:
        previous = json.load(f)
    changed = [name for name, digest in cache_state.items() if previous.get(name) != digest]
    if changed:
        print(" > AGS2 Cache Miss:", ", ".join(changed))
    else:
        print(" > AGS2 Cache Miss: cache payload missing")

def save_ags2_tree_state(cache_state: dict) -> None:
    state_path = get_ags2_tree_state_path()
    util.make_dir(os.path.dirname(state_path))
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(cache_state, f, sort_keys=True, separators=(",", ":"))

def prune_cache_root(cache_root: str, keep_dirs=None, keep_files=None) -> None:
    if not util.is_dir(cache_root):
        return
    keep_dir_names = set(keep_dirs or [])
    keep_file_names = set(keep_files or [])
    for name in os.listdir(cache_root):
        path = util.path(cache_root, name)
        if name.endswith(".tmp"):
            util.rm_path(path)
            continue
        if util.is_dir(path):
            if name not in keep_dir_names:
                util.rm_path(path)
            continue
        if keep_files is not None and util.is_file(path) and name not in keep_file_names:
            util.rm_path(path)

def prune_interrupted_cache_artifacts() -> None:
    cache_root = paths.cache()
    for relpath in [
        "ags2-tree",
        "ags2-subtree",
        "ags2-auto",
        "archive-tree",
        "archive-extract",
        "base-hdf",
        "pfs-partitions",
    ]:
        root = util.path(cache_root, relpath)
        if not util.is_dir(root):
            continue
        for name in os.listdir(root):
            if name.endswith(".tmp"):
                util.rm_path(util.path(root, name))

def prune_build_caches(
    base_hdf_cache_dir: str | None,
    ags2_cache_key: str,
    menu_subtree_cache_keys: list[str],
    autoentries_cache_key: str | None,
    archive_tree_cache_key: str | None,
    archive_extract_cache_keys: set[str],
    pfs_partition_cache_key: str | None,
) -> None:
    cache_root = paths.cache()

    base_hdf_keep = []
    if base_hdf_cache_dir:
        base_hdf_keep.append(os.path.basename(base_hdf_cache_dir))
    prune_cache_root(util.path(cache_root, "base-hdf"), keep_dirs=base_hdf_keep)

    ags2_tree_keep = [ags2_cache_key]
    ags2_tree_state = os.path.basename(get_ags2_tree_state_path())
    prune_cache_root(util.path(cache_root, "ags2-tree"), keep_dirs=ags2_tree_keep, keep_files=[ags2_tree_state])

    prune_cache_root(util.path(cache_root, "ags2-subtree"), keep_dirs=menu_subtree_cache_keys)

    auto_keep = [autoentries_cache_key] if autoentries_cache_key else []
    prune_cache_root(util.path(cache_root, "ags2-auto"), keep_dirs=auto_keep)

    archive_tree_keep = [archive_tree_cache_key] if archive_tree_cache_key else []
    prune_cache_root(util.path(cache_root, "archive-tree"), keep_dirs=archive_tree_keep)

    prune_cache_root(util.path(cache_root, "archive-extract"), keep_dirs=sorted(archive_extract_cache_keys))

    pfs_keep = [pfs_partition_cache_key + ".json"] if pfs_partition_cache_key else []
    prune_cache_root(util.path(cache_root, "pfs-partitions"), keep_files=pfs_keep)

def get_ags2_tree_cache_paths(cache_key: str) -> tuple[str, str]:
    cache_root = util.path(paths.cache(), "ags2-tree", cache_key)
    return (
        util.path(cache_root, "AGS2"),
        util.path(cache_root, "collection.json"),
    )

def load_collection_snapshot(path: str, collection: EntryCollection) -> None:
    with open(path, "r", encoding="utf-8") as f:
        snapshot = json.load(f)
    collection.image_entries = snapshot.get("image_entries", {})
    collection.by_id = {entry["id"]: entry for entry in snapshot.get("entries", [])}
    collection.path_sort_rank = {k: int(v) for k, v in snapshot.get("path_sort_rank", {}).items()}
    collection.path_ids = {
        (row[0], row[1])
        for row in snapshot.get("path_ids", [])
        if isinstance(row, list) and len(row) == 2
    }

def save_collection_snapshot(path: str, collection: EntryCollection) -> None:
    util.make_dir(os.path.dirname(path))
    snapshot = {
        "image_entries": collection.image_entries,
        "entries": list(collection.by_id.values()),
        "path_sort_rank": collection.path_sort_rank,
        "path_ids": sorted([list(row) for row in collection.path_ids]),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, sort_keys=True, separators=(",", ":"))

def relativize_collection_snapshot(snapshot: dict, root_path: str) -> dict:
    normalized_root = os.path.abspath(root_path)
    rel_snapshot = {
        "image_entries": snapshot.get("image_entries", {}),
        "entries": snapshot.get("entries", []),
        "path_sort_rank": {},
        "path_ids": [],
    }
    for path, rank in snapshot.get("path_sort_rank", {}).items():
        rel_snapshot["path_sort_rank"][os.path.relpath(path, normalized_root)] = int(rank)
    for row in snapshot.get("path_ids", []):
        if isinstance(row, list) and len(row) == 2:
            rel_snapshot["path_ids"].append([row[0], os.path.relpath(row[1], normalized_root)])
    return rel_snapshot

def merge_collection_snapshot(snapshot: dict, collection: EntryCollection, root_path: str | None = None) -> None:
    collection.image_entries.update(snapshot.get("image_entries", {}))
    normalized_root = os.path.abspath(root_path) if root_path else None
    for entry in snapshot.get("entries", []):
        if isinstance(entry, dict) and entry.get("id"):
            collection.by_id[entry["id"]] = entry
    for path, rank in snapshot.get("path_sort_rank", {}).items():
        merged_path = util.path(normalized_root, path) if normalized_root else path
        collection.path_sort_rank[merged_path] = int(rank)
    for row in snapshot.get("path_ids", []):
        if isinstance(row, list) and len(row) == 2:
            merged_path = util.path(normalized_root, row[1]) if normalized_root else row[1]
            collection.path_ids.add((row[0], merged_path))

def restore_ags2_tree_cache(cache_key: str, amiga_ags_path: str, collection: EntryCollection) -> bool:
    cache_ags2_path, cache_collection_path = get_ags2_tree_cache_paths(cache_key)
    if not util.is_dir(cache_ags2_path) or not util.is_file(cache_collection_path):
        return False
    util.rm_path(amiga_ags_path)
    util.clone_tree(cache_ags2_path, amiga_ags_path)
    load_collection_snapshot(cache_collection_path, collection)
    return True

def restore_ags2_collection_snapshot(cache_key: str, collection: EntryCollection) -> bool:
    _, cache_collection_path = get_ags2_tree_cache_paths(cache_key)
    if not util.is_file(cache_collection_path):
        return False
    load_collection_snapshot(cache_collection_path, collection)
    return True

def save_ags2_tree_cache(cache_key: str, amiga_ags_path: str, collection: EntryCollection) -> None:
    cache_ags2_path, cache_collection_path = get_ags2_tree_cache_paths(cache_key)
    cache_root = os.path.dirname(cache_ags2_path)
    tmp_root = cache_root + ".tmp"
    util.rm_path(tmp_root)
    util.make_dir(tmp_root)
    util.clone_tree(amiga_ags_path, util.path(tmp_root, "AGS2"))
    save_collection_snapshot(util.path(tmp_root, "collection.json"), collection)
    util.rm_path(cache_root)
    os.rename(tmp_root, cache_root)

def supports_top_level_menu_cache(menu) -> bool:
    try:
        items = flatten_top_level_menu_items(menu)
    except ValueError:
        return False
    for item in items:
        if not (isinstance(item, dict) and len(item) == 1):
            return False
    return True

def flatten_top_level_menu_items(menu) -> list:
    if not isinstance(menu, list):
        raise ValueError("menu is not a list")
    items = []
    for item in menu:
        if isinstance(item, list):
            for nested in item:
                if not isinstance(nested, dict):
                    raise ValueError("nested top-level item is not a dict")
                items.append(nested)
        else:
            if not isinstance(item, dict):
                raise ValueError("top-level item is not a dict")
            items.append(item)
    return items

def get_menu_subtree_cache_paths(cache_key: str) -> tuple[str, str]:
    cache_root = util.path(paths.cache(), "ags2-subtree", cache_key)
    return (
        util.path(cache_root, "AGS2"),
        util.path(cache_root, "collection.json"),
    )

def get_menu_subtree_cache_state(item, index: int, db_path: str, base_ags2: str, runscript_template_path: str, args) -> dict:
    return {
        "index": index,
        "item": hash_payload(item),
        "db": hash_payload(fingerprint_file(db_path)),
        "base_ags2": hash_payload(fingerprint_tree(base_ags2)),
        "runscript_template": hash_payload(fingerprint_file(runscript_template_path)),
        "args": hash_payload({
            "all_games": bool(args.all_games),
            "all_demos": bool(args.all_demos),
            "all_demoscene": bool(args.all_demoscene),
            "auto_lists": bool(args.auto_lists),
            "chipset_profile": getattr(args, "chipset_profile", "any"),
            "ecs_workspace": paths.tmp() if getattr(args, "chipset_profile", "any") == "ecs" else None,
        }),
        "behavior": AGS2_TREE_BEHAVIOR_FINGERPRINT,
    }

def get_menu_subtree_cache_key(cache_state: dict) -> str:
    return hash_payload(cache_state)

def restore_menu_subtree_cache(cache_key: str, amiga_ags_path: str, collection: EntryCollection) -> bool:
    cache_ags2_path, cache_collection_path = get_menu_subtree_cache_paths(cache_key)
    if not util.is_dir(cache_ags2_path) or not util.is_file(cache_collection_path):
        return False
    util.clone_tree(cache_ags2_path, amiga_ags_path)
    with open(cache_collection_path, "r", encoding="utf-8") as f:
        snapshot = json.load(f)
    merge_collection_snapshot(snapshot, collection, amiga_ags_path)
    return True

def save_menu_subtree_cache(cache_key: str, subtree_ags_path: str, collection: EntryCollection) -> None:
    cache_ags2_path, cache_collection_path = get_menu_subtree_cache_paths(cache_key)
    cache_root = os.path.dirname(cache_ags2_path)
    tmp_root = cache_root + ".tmp"
    util.rm_path(tmp_root)
    util.make_dir(tmp_root)
    util.clone_tree(subtree_ags_path, util.path(tmp_root, "AGS2"))
    rel_snapshot = relativize_collection_snapshot({
        "image_entries": collection.image_entries,
        "entries": list(collection.by_id.values()),
        "path_sort_rank": collection.path_sort_rank,
        "path_ids": [list(row) for row in collection.path_ids],
    }, subtree_ags_path)
    with open(util.path(tmp_root, "collection.json"), "w", encoding="utf-8") as f:
        json.dump(rel_snapshot, f, sort_keys=True, separators=(",", ":"))
    util.rm_path(cache_root)
    os.rename(tmp_root, cache_root)

def build_top_level_menu_with_cache(
    db: Connection,
    collection: EntryCollection,
    amiga_ags_path: str,
    menu,
    db_path: str,
    base_ags2: str,
    runscript_template_path: str,
    args,
    runscript_template: str,
    verbose: bool,
) -> None:
    items = flatten_top_level_menu_items(menu)
    restored_count = 0
    built_count = 0
    for index, item in enumerate(items):
        cache_key = get_menu_subtree_cache_key(
            get_menu_subtree_cache_state(item, index, db_path, base_ags2, runscript_template_path, args)
        )
        restored = restore_menu_subtree_cache(cache_key, amiga_ags_path, collection)
        if restored:
            restored_count += 1
            collection.progress_current += count_tree_entries([item])
            update_progress(collection, verbose)
            continue
        with tempfile.TemporaryDirectory(prefix="ags2-subtree-", dir=paths.tmp()) as subtree_root:
            subtree_collection = EntryCollection()
            make_tree(db, subtree_collection, subtree_root, [item], template=runscript_template, verbose=verbose)
            util.clone_tree(subtree_root, amiga_ags_path)
            merge_collection_snapshot(relativize_collection_snapshot({
                "image_entries": subtree_collection.image_entries,
                "entries": list(subtree_collection.by_id.values()),
                "path_sort_rank": subtree_collection.path_sort_rank,
                "path_ids": [list(row) for row in subtree_collection.path_ids],
            }, subtree_root), collection, amiga_ags_path)
            collection.progress_current += count_tree_entries([item])
            update_progress(collection, verbose)
            save_menu_subtree_cache(cache_key, subtree_root, subtree_collection)
            built_count += 1
    if verbose:
        print("")
        print(" > Top-level subtree cache: {} hit, {} rebuilt".format(restored_count, built_count))

# -----------------------------------------------------------------------------

def get_archive_tree_cache_state(entries) -> dict:
    archive_keys = []
    for entry in entries:
        arc_path = get_archive_path(entry)
        if not arc_path:
            archive_keys.append({"id": entry.get("id", ""), "missing": True})
            continue
        archive_keys.append({
            "id": entry.get("id", ""),
            "cache": os.path.basename(get_archive_extract_cache_dir(arc_path, entry) or ""),
            "whd_dir": get_amiga_whd_dir(entry) or "",
        })
    return {
        "archives": hash_payload(sorted(archive_keys, key=lambda row: row["id"])),
        "behavior": ARCHIVE_TREE_BEHAVIOR_FINGERPRINT,
    }

def archive_entry_states(entries):
    result = {}
    for entry in entries:
        archive = get_archive_path(entry)
        result[entry["id"]] = {
            "cache": get_archive_extract_cache_dir(archive, entry) if archive else None,
            "destination": get_amiga_whd_dir(entry),
        }
    return result


def try_append_archives(clone_path, entries, current, workspace_state):
    previous = workspace_state.get("archive_entries")
    if (not previous or workspace_state.get("archive_behavior") != ARCHIVE_TREE_BEHAVIOR_FINGERPRINT
            or not Path(clone_path, "DH1", "WHD").is_dir()
            or any(current.get(i) != value for i, value in previous.items())):
        return False
    added = [entry for entry in entries if entry["id"] not in previous]
    with tempfile.TemporaryDirectory(prefix="archive-append-", dir=clone_path) as temporary:
        extract_entries(temporary, added, verbose=True)
        source = Path(temporary, "DH1", "WHD")
        target = Path(clone_path, "DH1", "WHD")
        if source.is_dir():
            # Archives can contain additional top-level files. Check actual
            # extraction results, including non-WHDLoad titles, before merging.
            names = {}
            for item in source.rglob("*"):
                if not item.is_file():
                    continue
                destination = target / item.relative_to(source)
                parent = destination.parent
                if parent not in names:
                    names[parent] = {p.name.casefold() for p in parent.iterdir()} if parent.is_dir() else set()
                if destination.name.casefold() in names[parent]:
                    return False
            workspace_state.pop("archive_entries", None)
            workspace_state.pop("archive_tree_cache_key", None)
            save_workspace_state(clone_path, workspace_state)
            util.copytree(str(source), str(target))
    print(" > Appended {} archive(s); preserved existing extracted files".format(len(added)))
    return True


def get_archive_tree_cache_key(cache_state: dict) -> str:
    return hash_payload(cache_state)

def get_archive_tree_cache_path(cache_key: str) -> str:
    return util.path(paths.cache(), "archive-tree", cache_key, "WHD")

def restore_archive_tree_cache(cache_key: str, clone_path: str) -> bool:
    cache_path = get_archive_tree_cache_path(cache_key)
    if not util.is_dir(cache_path):
        return False
    util.clone_tree(cache_path, util.path(clone_path, "DH1", "WHD"))
    return True

def save_archive_tree_cache(cache_key: str, clone_path: str) -> None:
    source_path = util.path(clone_path, "DH1", "WHD")
    if not util.is_dir(source_path):
        return
    cache_path = get_archive_tree_cache_path(cache_key)
    cache_root = os.path.dirname(cache_path)
    tmp_root = cache_root + ".tmp"
    util.rm_path(tmp_root)
    util.make_dir(tmp_root)
    util.clone_tree(source_path, util.path(tmp_root, "WHD"))
    util.rm_path(cache_root)
    os.rename(tmp_root, cache_root)

def get_menu_subtree_cache_keys(menu, db_path: str, base_ags2: str, runscript_template_path: str, args) -> list[str]:
    items = flatten_top_level_menu_items(menu)
    return [
        get_menu_subtree_cache_key(
            get_menu_subtree_cache_state(item, index, db_path, base_ags2, runscript_template_path, args)
        )
        for index, item in enumerate(items)
    ]

def get_pfs_partition_cache_state(
    base_hdf_cache_dir: str,
    menu_subtree_cache_keys: list[str],
    autoentries_cache_key: str | None,
    archive_tree_cache_key: str,
    layer_sources: list[tuple[str, str]],
    add_dirs: list[str] | None,
) -> dict:
    layers = []
    for src_dir, dst in layer_sources:
        layers.append({
            "src": os.path.abspath(src_dir),
            "dst": dst,
            "tree": hash_payload(fingerprint_tree(src_dir)),
        })
    extra_dirs = []
    for spec in add_dirs or []:
        src_dir, dst = spec.split("::", 1)
        extra_dirs.append({
            "src": os.path.abspath(src_dir),
            "dst": dst,
            "tree": hash_payload(fingerprint_tree(src_dir)),
        })
    return {
        "base_hdf_cache_dir": base_hdf_cache_dir,
        "menu_subtrees": menu_subtree_cache_keys,
        "autoentries_cache_key": autoentries_cache_key or "",
        "archive_tree_cache_key": archive_tree_cache_key,
        "layers": layers,
        "hires_assets": hash_payload([fingerprint_tree("data/ags2-highres"), fingerprint_tree("data/img_highres")]),
        "hires_behavior": fingerprint_python_defs("build/ags_make.py", ["make_hires_tree", "make_hires_artwork"]),
        "hires_encoder": [fingerprint_file("build/repair_hires_palettes.py"), fingerprint_file("build/iff_ilbm.py")],
        "extra_dirs": extra_dirs,
        "behavior": PFS_PARTITION_BEHAVIOR_FINGERPRINT,
    }

def get_pfs_partition_cache_key(cache_state: dict) -> str:
    return hash_payload(cache_state)

def get_add_dirs_cache_state(add_dirs: list[str] | None) -> list[dict]:
    state = []
    for spec in add_dirs or []:
        src_dir, dst = spec.split("::", 1)
        state.append({
            "src": os.path.abspath(src_dir),
            "dst": dst,
            "tree": hash_payload(fingerprint_tree(src_dir)),
        })
    return state

def get_add_dirs_destinations(add_dirs: list[str] | None) -> list[str]:
    destinations = []
    for spec in add_dirs or []:
        _, dst = spec.split("::", 1)
        destinations.append(dst)
    return destinations

def count_files_in_tree(path: str) -> int:
    total = 0
    for _, _, files in os.walk(path):
        total += sum(1 for name in files if name != ".DS_Store")
    return total

def print_add_dir_progress(src_dir: str, verbose: bool, prefix: str = "    > ") -> None:
    entries = sorted(os.listdir(src_dir), key=str.casefold)
    top_dirs = [name for name in entries if util.is_dir(util.path(src_dir, name))]
    top_files = [name for name in entries if util.is_file(util.path(src_dir, name)) and name != ".DS_Store"]

    for index, name in enumerate(top_dirs, start=1):
        src_path = util.path(src_dir, name)
        if verbose:
            print("{}{}. {} ({} files)".format(prefix, index, name, count_files_in_tree(src_path)))

    file_offset = len(top_dirs)
    for index, name in enumerate(top_files, start=1):
        if verbose:
            print("{}{}. {} (file)".format(prefix, file_offset + index, name))

def copy_add_dir_with_progress(src_dir: str, dest: str, verbose: bool) -> None:
    entries = sorted(os.listdir(src_dir), key=str.casefold)
    top_dirs = [name for name in entries if util.is_dir(util.path(src_dir, name))]
    top_files = [name for name in entries if util.is_file(util.path(src_dir, name)) and name != ".DS_Store"]

    util.make_dir(dest)

    print_add_dir_progress(src_dir, verbose)

    for name in top_dirs:
        src_path = util.path(src_dir, name)
        dest_path = util.path(dest, name)
        util.clone_tree(src_path, dest_path)

    for name in top_files:
        src_path = util.path(src_dir, name)
        dest_path = util.path(dest, name)
        shutil.copy2(src_path, dest_path)

def remove_ignored_host_files(path: str) -> None:
    for root, _, files in os.walk(path):
        for name in files:
            if name == ".DS_Store":
                os.remove(util.path(root, name))

def get_pfs_partition_cache_path(cache_key: str) -> str:
    return util.path(paths.cache(), "pfs-partitions", cache_key + ".json")

def restore_pfs_partition_cache(cache_key: str, workspace_state: dict) -> list[tuple[str, int]] | None:
    candidates = []
    cache_path = get_pfs_partition_cache_path(cache_key)
    if util.is_file(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            candidates.append(json.load(f))
    if workspace_state.get("pfs_partition_cache_key") == cache_key:
        candidates.append(workspace_state.get("pfs_partitions"))
    for raw_partitions in candidates:
        if not isinstance(raw_partitions, list) or not raw_partitions:
            continue
        parsed = []
        for row in raw_partitions:
            if isinstance(row, dict) and "name" in row and "cyls" in row:
                parsed.append((str(row["name"]), int(row["cyls"])))
        if parsed:
            return parsed
    return None

def save_pfs_partition_cache(cache_key: str, partitions: list[tuple[str, int]], workspace_state: dict) -> None:
    raw_partitions = [{"name": name, "cyls": cyls} for name, cyls in partitions]
    cache_path = get_pfs_partition_cache_path(cache_key)
    util.make_dir(os.path.dirname(cache_path))
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(raw_partitions, f, sort_keys=True, separators=(",", ":"))
    workspace_state["pfs_partition_cache_key"] = cache_key
    workspace_state["pfs_partitions"] = raw_partitions

AUTO_ROOT_DIR_KEYS = [
    "allgames",
    "allgames_year",
    "allgames_nonenglish",
]

AUTO_SCENE_DIR_KEYS = [
    "demos",
    "demos_country",
    "demos_group",
    "demos_year",
    "demos_cracktro",
    "demos_intro",
    "diskmags",
    "diskmags_date",
    "musicdisks",
    "musicdisks_year",
    "slideshows",
]

AUTO_NONENGLISH_DIR_KEYS = [
    "unique_nonenglish",
]

def get_autoentries_cache_paths(cache_key: str) -> tuple[str, str]:
    cache_root = util.path(paths.cache(), "ags2-auto", cache_key)
    return (
        util.path(cache_root, "AGS2"),
        util.path(cache_root, "collection.json"),
    )

def get_autoentries_cache_state(collection: EntryCollection, args) -> dict:
    entries = sorted([entry for entry in collection.by_id.values() if isinstance(entry, dict) and entry.get("id")], key=lambda e: e["id"])
    return {
        "entries": hash_payload(entries),
        "args": hash_payload({
            "all_games": bool(args.all_games),
            "all_demos": bool(args.all_demos),
            "all_demoscene": bool(args.all_demoscene),
            "auto_lists": bool(args.auto_lists),
            "chipset_profile": getattr(args, "chipset_profile", "any"),
            "ecs_workspace": paths.tmp() if getattr(args, "chipset_profile", "any") == "ecs" else None,
        }),
        "behavior": AUTOENTRIES_BEHAVIOR_FINGERPRINT,
    }

def get_autoentries_cache_key(cache_state: dict) -> str:
    return hash_payload(cache_state)

def get_autoentries_generated_relpaths() -> list[str]:
    relpaths = []
    for key in AUTO_ROOT_DIR_KEYS:
        name = strings["dirs"][key]
        relpaths.extend([name + ".ags", name + ".txt", name + ".iff"])
    scene_root = strings["dirs"]["scene"] + ".ags"
    scene_name = strings["dirs"]["scene"]
    relpaths.extend([scene_name + ".txt", scene_name + ".iff"])
    for key in AUTO_SCENE_DIR_KEYS:
        name = strings["dirs"][key]
        relpaths.extend([
            util.path(scene_root, name + ".ags"),
            util.path(scene_root, name + ".txt"),
            util.path(scene_root, name + ".iff"),
        ])
    nonenglish_root = strings["dirs"]["allgames_nonenglish"] + ".ags"
    for key in AUTO_NONENGLISH_DIR_KEYS:
        name = strings["dirs"][key]
        relpaths.extend([
            util.path(nonenglish_root, name + ".ags"),
            util.path(nonenglish_root, name + ".txt"),
            util.path(nonenglish_root, name + ".iff"),
        ])
    return relpaths

def is_autoentries_relpath(relpath: str) -> bool:
    normalized = relpath.replace("\\", "/")
    for candidate in get_autoentries_generated_relpaths():
        candidate_norm = candidate.replace("\\", "/")
        if normalized == candidate_norm or normalized.startswith(candidate_norm + "/"):
            return True
    return False

def collect_autoentries_tree_snapshot(ags_path: str, dest_root: str) -> None:
    for relpath in get_autoentries_generated_relpaths():
        source_path = util.path(ags_path, relpath)
        if util.is_dir(source_path):
            util.clone_tree(source_path, util.path(dest_root, relpath))
        elif util.is_file(source_path):
            util.make_dir(os.path.dirname(util.path(dest_root, relpath)))
            shutil.copy2(source_path, util.path(dest_root, relpath))

def extract_autoentries_collection_delta(ags_path: str, before_path_ids: set, before_sort_rank: dict, collection: EntryCollection) -> dict:
    delta_path_ids = []
    for entry_id, path in sorted(collection.path_ids - before_path_ids):
        relpath = os.path.relpath(path, ags_path)
        if is_autoentries_relpath(relpath):
            delta_path_ids.append([entry_id, relpath])
    delta_sort_rank = {}
    for path, rank in collection.path_sort_rank.items():
        if before_sort_rank.get(path) == rank:
            continue
        relpath = os.path.relpath(path, ags_path)
        if is_autoentries_relpath(relpath):
            delta_sort_rank[relpath] = int(rank)
    return {
        "entries": [],
        "image_entries": {path: entry_id for path, entry_id in collection.image_entries.items() if is_autoentries_relpath(path)},
        "path_ids": delta_path_ids,
        "path_sort_rank": delta_sort_rank,
    }

def restore_autoentries_cache(cache_key: str, amiga_ags_path: str, collection: EntryCollection) -> bool:
    cache_ags2_path, cache_collection_path = get_autoentries_cache_paths(cache_key)
    if not util.is_dir(cache_ags2_path) or not util.is_file(cache_collection_path):
        return False
    util.clone_tree(cache_ags2_path, amiga_ags_path)
    with open(cache_collection_path, "r", encoding="utf-8") as f:
        snapshot = json.load(f)
    merge_collection_snapshot(snapshot, collection, amiga_ags_path)
    return True

def save_autoentries_cache(cache_key: str, amiga_ags_path: str, collection_delta: dict) -> None:
    cache_ags2_path, cache_collection_path = get_autoentries_cache_paths(cache_key)
    cache_root = os.path.dirname(cache_ags2_path)
    tmp_root = cache_root + ".tmp"
    util.rm_path(tmp_root)
    util.make_dir(tmp_root)
    collect_autoentries_tree_snapshot(amiga_ags_path, util.path(tmp_root, "AGS2"))
    with open(util.path(tmp_root, "collection.json"), "w", encoding="utf-8") as f:
        json.dump(collection_delta, f, sort_keys=True, separators=(",", ":"))
    util.rm_path(cache_root)
    os.rename(tmp_root, cache_root)

# -----------------------------------------------------------------------------

def make_clone_progress_lines(clone_path: str) -> list[str]:
    stats_paths = [
        ("DH0", util.path(clone_path, "DH0")),
        ("DH1/AGS2", util.path(clone_path, "DH1", "AGS2")),
        ("DH1/AGS-HiRes", util.path(clone_path, "DH1", "AGS-HiRes")),
        ("DH1/Music", util.path(clone_path, "DH1", "Music")),
    ]
    whd_stats_paths = [
        ("DH1/WHD/D", util.path(clone_path, "DH1", "WHD", "D")),
        ("DH1/WHD/G", util.path(clone_path, "DH1", "WHD", "G")),
        ("DH1/WHD/M", util.path(clone_path, "DH1", "WHD", "M")),
        ("DH1/WHD/N", util.path(clone_path, "DH1", "WHD", "N")),
    ]
    lines = [
        "Clone payload summary:",
        "  Stage                    Files   Dirs   Size",
    ]
    for label, path in stats_paths:
        if util.is_dir(path):
            stats = util.get_tree_stats(path)
            lines.append(
                "  {:<22} {:>7} {:>6} {:>8}".format(
                    label,
                    stats["files"],
                    stats["dirs"],
                    util.format_bytes(stats["bytes"]),
                )
            )
    lines.append("")
    lines.append("  WHD subdirectories:")
    lines.append("  Stage                    Files   Dirs   Size")
    for label, path in whd_stats_paths:
        if util.is_dir(path):
            stats = util.get_tree_stats(path)
            lines.append(
                "  {:<22} {:>7} {:>6} {:>8}".format(
                    label,
                    stats["files"],
                    stats["dirs"],
                    util.format_bytes(stats["bytes"]),
                )
            )
    lines.append("")
    lines.append("Amiga clone stages:")
    lines.append("  DH0")
    lines.append("  WHD (D, G, M, N)")
    lines.append("  Music")
    return lines

def write_clone_progress(clone_path: str, lines=None) -> None:
    with open(util.path(clone_path, "clone-progress"), mode="w", encoding="latin-1", errors="replace") as f:
        f.write("\n".join(lines if lines is not None else make_clone_progress_lines(clone_path)) + "\n")

def inject_clone_progress(clone_script_path: str, clone_path: str, lines=None) -> None:
    progress_block = "\n".join('echo "{}"'.format(line.replace('"', "'")) for line in (lines if lines is not None else make_clone_progress_lines(clone_path)))
    with open(clone_script_path, "r", encoding="latin-1", errors="replace") as f:
        script = f.read()
    script = script.replace(
        'if exists tmp:clone-progress\n  type tmp:clone-progress\nendif',
        progress_block
    )
    with open(clone_script_path, "w", encoding="latin-1", errors="replace") as f:
        f.write(script)

# -----------------------------------------------------------------------------

def add_all(db: Connection, c: EntryCollection, category: str, exclude_subcategories=None) -> None:
    if getattr(db, 'ecs_selector', None):
        for row in db.execute('SELECT * FROM titles WHERE category=? AND (redundant IS NULL OR redundant="")', (category,)):
            entry = db.ecs_selector.resolve(row['id'])
            if entry and not any((entry.get('subcategory') or '').lower().startswith(s.lower())
                                 for s in (exclude_subcategories or [])):
                c.by_id[entry['id']] = entry
        return
    for r in db.cursor().execute('SELECT * FROM titles WHERE category=? AND (redundant IS NULL OR redundant="")', (category,)):
        entry = sanitize_entry(r)
        if not entry and r["archive_path"]:
            archive_path = r["archive_path"]
            archive_full_path = util.path(paths.titles(), archive_path)
            if not util.is_file(archive_full_path):
                warn_missing_archive(r["title_short"] or r["id"], archive_path)
        preferred_entry = get_preferred_entry(db, entry)
        if entry:
            if exclude_subcategories:
                exclude_entry = False
                for subcategory in exclude_subcategories:
                    if entry.get("subcategory", "").lower().startswith(subcategory.lower()): exclude_entry = True
                if not exclude_entry:
                    c.by_id[entry["id"]] = entry
            else:
                c.by_id[entry["id"]] = entry
        if preferred_entry:
            if exclude_subcategories:
                exclude_entry = False
                for subcategory in exclude_subcategories:
                    if preferred_entry.get("subcategory", "").lower().startswith(subcategory.lower()): exclude_entry = True
                if not exclude_entry:
                    c.by_id[preferred_entry["id"]] = preferred_entry
            else:
                c.by_id[preferred_entry["id"]] = preferred_entry

def iter_requested_menu_names(node):
    if isinstance(node, str):
        yield node
        return
    if isinstance(node, list):
        for item in node:
            yield from iter_requested_menu_names(item)
        return
    if isinstance(node, dict):
        for key, value in node.items():
            if key in {"image", "note", "ordering", "rank", "hidden"}:
                continue
            if isinstance(value, dict):
                yield key
            else:
                yield from iter_requested_menu_names(value)

def audit_missing_archives(db: Connection, menu, args) -> None:
    names = list(iter_requested_menu_names(menu))
    requested, missing_rows = audit_missing_archive_entries(db, names)
    for name in names:
        missing_entry = requested.get(name)
        if missing_entry:
            warn_missing_archive(name, missing_entry["archive_path"])

    categories: list[tuple[str, list[str] | None]] = []
    if args.all_games:
        categories.append(("Game", None))
    if args.all_demos:
        categories.append(("Demo", ["Disk Magazine", "Slide Show"]))
    if args.all_demoscene:
        categories.append(("Demo", None))

    for category, exclude_subcategories in categories:
        for row in missing_rows:
            if row['category'] != category or row['redundant'] not in (None, ''):
                continue
            if exclude_subcategories:
                subcategory = (row["subcategory"] or "").lower()
                if any(subcategory.startswith(excluded.lower()) for excluded in exclude_subcategories):
                    continue
            warn_missing_archive(row["title_short"] or row["id"], row["archive_path"])


def get_archive_extract_cache_dir(arc_path: str, entry) -> str | None:
    stat = os.stat(arc_path)
    key_source = "|".join([
        os.path.abspath(arc_path),
        str(stat.st_size),
        str(stat.st_mtime_ns),
        entry.get("id", ""),
        entry.get("slave_dir", ""),
        "notwhdl" if entry_is_notwhdl(entry) else "whdl",
    ])
    key = hashlib.sha1(key_source.encode("utf-8")).hexdigest()
    return util.path(paths.cache(), "archive-extract", key)

def get_unique_archive_entries(entries):
    seen = set()
    unique = []
    for entry in entries:
        archive_path = entry.get("archive_path")
        if not archive_path or archive_path in seen:
            continue
        seen.add(archive_path)
        unique.append(entry)
    return unique

def get_archive_extract_cache_keys(entries) -> set[str]:
    keys = set()
    for entry in get_unique_archive_entries(entries):
        arc_path = get_archive_path(entry)
        if not arc_path:
            continue
        cache_dir = get_archive_extract_cache_dir(arc_path, entry)
        if cache_dir:
            keys.add(os.path.basename(cache_dir))
    return keys

def extract_entries(clone_path, entries, verbose=False):
    pending = get_unique_archive_entries(entries)
    total = len(pending)
    if total == 0:
        return

    max_workers = min(4, os.cpu_count() or 1, total)
    if max_workers <= 1:
        for done, entry in enumerate(pending, start=1):
            if verbose:
                print("\r > Extracting archives [{}/{}]".format(done, total), end="", flush=True)
            extract_entry(clone_path, entry)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(extract_entry, clone_path, entry) for entry in pending]
            done = 0
            for future in as_completed(futures):
                future.result()
                done += 1
                if verbose:
                    print("\r > Extracting archives [{}/{}]".format(done, total), end="", flush=True)
    if verbose and total > 0:
        print("")

def extract_entry(clone_path, entry):
    arc_path = get_archive_path(entry)
    if not arc_path:
        print(" > WARNING: archive not found for", entry["id"])
    else:
        dest = get_whd_dir(clone_path, entry)
        cache_dir = get_archive_extract_cache_dir(arc_path, entry)
        if cache_dir and util.is_dir(cache_dir):
            util.clone_tree(cache_dir, dest)
            return

        extracted_path = dest
        if cache_dir:
            util.make_dir(os.path.dirname(cache_dir))
            extracted_path = cache_dir + ".tmp"
            util.rm_path(extracted_path)

        util.lha_extract(arc_path, extracted_path)
        if not entry_is_notwhdl(entry):
            info_path = util.path(extracted_path, entry["slave_dir"] + ".info")
            if util.is_file(info_path):
                os.remove(info_path)

        if cache_dir:
            util.rm_path(cache_dir)
            os.rename(extracted_path, cache_dir)
            util.clone_tree(cache_dir, dest)

# -----------------------------------------------------------------------------
# command line interface

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", dest="config_file", required=True, metavar="FILE", type=lambda x: util.argparse_is_file(parser, x),  help="configuration file")
    parser.add_argument("-o", "--out-dir", dest="out_dir", metavar="FILE", type=lambda x: util.argparse_is_dir(parser, x),  help="output directory")
    parser.add_argument("--incremental", action="store_true", help="prepare a transactional incremental Amiberry image update")
    parser.add_argument("--image-size-bytes", type=int, default=16_000_000_000,
                        help="maximum whole-image size in decimal bytes (default: 16 GB; 0 sizes to payload)")
    parser.add_argument("--boot-extra-bytes", type=int, default=200_000_000,
                        help="additional DH0 reserve in decimal bytes (default: 200 MB)")
    base_source = parser.add_mutually_exclusive_group()
    base_source.add_argument("-b", "--base-hdf", dest="base_hdf", metavar="FILE", help="use a legacy base HDF instead of the native base directory")
    base_source.add_argument("--base-dir", metavar="DIR", help="native base directory (default: AGSBASE or sibling AV-Base checkout)")
    parser.add_argument("-a", "--ags-dir", dest="ags_dir", metavar="FILE", type=lambda x: util.argparse_is_dir(parser, x),  help="AGS2 configuration directory")
    parser.add_argument("-d", "--add-dir", dest="add_dirs", action="append", help="add dir to amiga filesystem (example '~/Amiga/Music::DH1:Music')")

    parser.add_argument("--all-games", dest="all_games", action="store_true", default=False, help="include all games")
    parser.add_argument("--all-demos", dest="all_demos", action="store_true", default=False, help="include all demos")
    parser.add_argument("--all-demoscene", dest="all_demoscene", action="store_true", default=False, help="include all demo scene content")
    parser.add_argument("--auto-lists", dest="auto_lists", action="store_true", default=False, help="create automatic lists")
    parser.add_argument("--only-ags-tree", dest="only_ags_tree", action="store_true", default=False, help="only generate AGS tree")
    parser.add_argument('--chipset-profile', choices=['any', 'ecs'], default='any', help='Select compatible canonical versions for the build')
    parser.add_argument('--temp-dir', help='Override the temporary workspace after .env has loaded')

    
    print("Build started: ")
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    try:
        paths.verify()
        args = parser.parse_args()
        if args.image_size_bytes < 0 or args.boot_extra_bytes < 0:
            raise ValueError("Image size and DH0 reserve must be nonnegative")
        if args.temp_dir:
            os.environ['AGSTEMP'] = os.path.abspath(args.temp_dir)
        elif args.chipset_profile == 'ecs':
            os.environ['AGSTEMP'] = paths.tmp() + '-ECS'
        if args.chipset_profile == 'ecs':
            os.environ['AGSCACHEGEN'] = 'ecs'
            if not Path('data/img_ecs/manifest.json').is_file():
                raise FileNotFoundError('Static ECS artwork missing; run make ecs-artwork first')
        timings = []

        with timed_step(timings, "db setup"):
            db = util.get_db(True)
            collection = EntryCollection()
            if args.chipset_profile == 'ecs':
                from ags_ecs import ECSSelector, ECSDatabase, make_sanitizer
                overrides = json.loads(Path('configs/ecs-preferred-versions.json').read_text())
                sanitize_ecs = make_sanitizer(sanitize_entry)
                selector = ECSSelector(db.execute('SELECT * FROM titles'), sanitize_ecs, overrides)
                selector.report.extend(sanitize_ecs.excluded)
                selector.write_report(util.path(paths.cache(), 'ecs-selection-report.json'))
                ambiguous = [r for r in selector.report if r['status'] == 'ambiguous']
                if ambiguous:
                    raise ValueError('Ambiguous ECS fallback families; curate configs/ecs-preferred-versions.json: ' + ', '.join(r['title'] for r in ambiguous))
                db = ECSDatabase(db, selector)

        if args.out_dir:
            out_dir = args.out_dir

        clone_path = paths.tmp()
        amiga_boot_path = util.path(clone_path, "DH0")
        amiga_data_path = util.path(clone_path, "DH1")
        amiga_ags_path = util.path(amiga_data_path, "AGS2")
        util.make_dir(clone_path)
        workspace_state = load_workspace_state(clone_path)
        prune_interrupted_cache_artifacts()

        data_dir = "data"
        if not util.is_dir(data_dir):
            raise IOError("data dir not found ({})".format(data_dir))

        # parse configuration
        config_dir = os.path.dirname(args.config_file)
        config_base_name = os.path.splitext(os.path.basename(args.config_file))[0]

        runscript_template_path = util.path(config_dir, config_base_name) + ".runscript"
        if not util.is_file(runscript_template_path):
            raise IOError("run script template not found ({})".format(runscript_template_path))

        with timed_step(timings, "parse config"):
            print("Parsing menu...")
            menu = util.yaml_load(args.config_file)
            if not isinstance(menu, list):
                raise ValueError("config file not a list ({})".format(args.config_file))
            excluded_titles = sorted(collect_excluded_titles(menu))
            if excluded_titles:
                excluded_title_set = set(excluded_titles)
                excluded_entry_ids = resolve_excluded_entry_ids(db, excluded_title_set)
                print(" > Excluding {} Mini title(s) from config ({} resolved IDs)".format(len(excluded_titles), len(excluded_entry_ids)))
                menu = prune_excluded_titles(menu, excluded_title_set, db, excluded_entry_ids)
            with open(runscript_template_path, 'r') as f:
                runscript_template = f.read()

        db_path = "data/db/titles.sqlite3"

        # Native DH0 is authoritative; legacy HDF input remains an explicit override.
        base_hdf = None
        base_directory = None if args.base_hdf else os.path.abspath(args.base_dir or paths.base())
        if base_directory:
            if not util.is_dir(base_directory):
                raise IOError("native base directory not found ({}); clone AV-Base alongside AmigaVision or set AGSBASE".format(base_directory))
            base_hdf_state = {
                "base_hdf": base_directory,
                "base_hdf_cache_dir": "native-v1-" + directory_fingerprint(base_directory),
            }
        else:
            base_hdf = args.base_hdf
            if not util.is_file(base_hdf):
                raise IOError("base HDF not found ({})".format(base_hdf))
            base_hdf_state = {
                "base_hdf": os.path.abspath(base_hdf),
                "base_hdf_cache_dir": get_base_hdf_cache_dir(base_hdf),
            }

        with timed_step(timings, "workspace init"):
            with timed_step(timings, "workspace cleanup"):
                if workspace_state.get("base_hdf") != base_hdf_state["base_hdf"] or workspace_state.get("base_hdf_cache_dir") != base_hdf_state["base_hdf_cache_dir"]:
                    util.rm_path(amiga_boot_path)
                    workspace_state.pop("ags2_cache_key", None)
                    workspace_state.pop("archive_tree_cache_key", None)
            with timed_step(timings, "workspace prepare"):
                util.make_dir(amiga_boot_path)

        if not args.only_ags_tree:
            with timed_step(timings, "stage base directory" if base_directory else "extract base hdf"):
                util.rm_path(amiga_boot_path)
                if base_directory:
                    print("Staging native base directory: {}".format(base_directory))
                    stage_directory(base_directory, amiga_boot_path)
                else:
                    print("Extracting base HDF image: {}".format(base_hdf))
                    used_cache = extract_base_image(base_hdf, amiga_boot_path)
                    if used_cache:
                        print(" > Using cached base HDF unpack")
                workspace_state["base_hdf"] = base_hdf_state["base_hdf"]
                workspace_state["base_hdf_cache_dir"] = base_hdf_state["base_hdf_cache_dir"]

        # Old base images and workspaces may still contain system-disk launchers.
        # Rebuild them on DH1 instead of retaining a second, stale copy on DH0.
        for launcher_name in ("AGS2", "AGS-HiRes"):
            util.rm_path(util.path(amiga_boot_path, launcher_name))

        # copy base AGS2 config
        print("Building AGS2 tree...")
        base_ags2 = args.ags_dir
        if not base_ags2:
            base_ags2 = util.path("data", "ags2")
        if not util.is_dir(base_ags2):
            raise IOError("configuration directory not found ({})".format(base_ags2))
        print(" > Using configuration: {}".format(base_ags2))

        ags2_cache_state = get_ags2_tree_cache_state(menu, db_path, base_ags2, runscript_template_path, args.config_file, args)
        ags2_cache_key = get_ags2_tree_cache_key(ags2_cache_state)
        hires_source_trees = {}
        with timed_step(timings, "check entry changes"):
            current_append_inputs = append_input_state(db, ags2_cache_state, hires_source_trees) if args.chipset_profile == "any" else None
        append_delta = None
        if workspace_state.get("ags2_cache_key") != ags2_cache_key and current_append_inputs:
            with timed_step(timings, "append launcher entries"):
                append_delta = try_append_launcher(
                    db, args, menu, workspace_state.get("append_inputs"), current_append_inputs,
                    clone_path, amiga_ags_path, collection, runscript_template, workspace_state)
        used_ags2_cache = append_delta is not None
        menu_subtree_cache_keys = []
        if supports_top_level_menu_cache(menu):
            menu_subtree_cache_keys = get_menu_subtree_cache_keys(
                menu,
                db_path,
                base_ags2,
                runscript_template_path,
                args,
            )
        autoentries_cache_key = None
        archive_tree_cache_key = None
        archive_extract_cache_keys = set()
        pfs_partition_cache_key = None

        with timed_step(timings, "copy ags2 base"):
            if used_ags2_cache:
                pass
            elif workspace_state.get("ags2_cache_key") == ags2_cache_key and util.is_dir(amiga_ags_path) and (
                restore_workspace_ags2_collection_snapshot(clone_path, collection)
                or restore_ags2_collection_snapshot(ags2_cache_key, collection)
            ):
                used_ags2_cache = True
                print(" > Reusing cached AGS2 workspace")
            elif not restore_ags2_tree_cache(ags2_cache_key, amiga_ags_path, collection):
                report_ags2_tree_cache_miss(ags2_cache_state)
                collection = EntryCollection()
                util.rm_path(amiga_ags_path)
                util.copytree(base_ags2, amiga_ags_path)
            else:
                used_ags2_cache = True
                print(" > Using cached AGS2 tree")

        if util.is_dir(amiga_ags_path) and collection.by_id:
            save_workspace_ags2_collection_snapshot(clone_path, collection)

        # collect entries
        if not used_ags2_cache:
            reset_warning_state()
            with timed_step(timings, "collect menu entries"):
                collection.progress_current = 0
                collection.progress_total = count_tree_entries(menu) + len(collection.by_id)
                if menu:
                    if supports_top_level_menu_cache(menu):
                        build_top_level_menu_with_cache(
                            db,
                            collection,
                            amiga_ags_path,
                            menu,
                            db_path,
                            base_ags2,
                            runscript_template_path,
                            args,
                            runscript_template,
                            True,
                        )
                    else:
                        make_tree(db, collection, amiga_ags_path, menu, template=runscript_template, verbose=True)
            with timed_step(timings, "collect all entries"):
                if args.all_games:
                    add_all(db, collection, "Game")
                if args.all_demos:
                    add_all(db, collection, "Demo", exclude_subcategories=["Disk Magazine", "Slide Show"])
                if args.all_demoscene:
                    add_all(db, collection, "Demo")
            with timed_step(timings, "build auto entries"):
                collection.progress_total = collection.progress_current + len(list(collection.ids()))
                if args.all_games or args.all_demos or args.all_demoscene or args.auto_lists:
                    autoentries_cache_key = get_autoentries_cache_key(get_autoentries_cache_state(collection, args))
                    if restore_autoentries_cache(autoentries_cache_key, amiga_ags_path, collection):
                        print(" > Using cached auto entries")
                    else:
                        before_path_ids = set(collection.path_ids)
                        before_sort_rank = dict(collection.path_sort_rank)
                        make_autoentries(collection, amiga_ags_path, games=args.all_games|args.auto_lists, demos=args.all_demos|args.all_demoscene|args.auto_lists)
                        save_autoentries_cache(
                            autoentries_cache_key,
                            amiga_ags_path,
                            extract_autoentries_collection_delta(amiga_ags_path, before_path_ids, before_sort_rank, collection),
                        )
                if collection.progress_total > 0:
                    print("")

            # generate run scripts
            with timed_step(timings, "generate runscripts"):
                make_runscripts(collection, amiga_ags_path, template=runscript_template)
            save_ags2_tree_cache(ags2_cache_key, amiga_ags_path, collection)
            save_ags2_tree_state(ags2_cache_state)
            workspace_state["ags2_cache_key"] = ags2_cache_key
        else:
            timings.append(("collect menu entries", 0.0))
            timings.append(("collect all entries", 0.0))
            timings.append(("build auto entries", 0.0))
            timings.append(("generate runscripts", 0.0))
            save_ags2_tree_state(ags2_cache_state)
            workspace_state["ags2_cache_key"] = ags2_cache_key

        if append_delta is not None:
            workspace_state["appended_workspace"] = True
        elif not used_ags2_cache:
            workspace_state.pop("appended_workspace", None)

        if args.all_games or args.all_demos or args.all_demoscene or args.auto_lists:
            autoentries_cache_key = get_autoentries_cache_key(get_autoentries_cache_state(collection, args))

        if util.is_dir(amiga_ags_path) and collection.by_id:
            save_workspace_ags2_collection_snapshot(clone_path, collection)

        reset_warning_state()
        with timed_step(timings, "audit missing archives"):
            audit_missing_archives(db, menu, args)

        # extract whdloaders
        if not args.only_ags_tree:
            with timed_step(timings, "extract archives"):
                print("Extracting {} content archives...".format(len(collection.by_id.items())))
                archive_tree_cache_key = get_archive_tree_cache_key(get_archive_tree_cache_state(collection.ids()))
                current_archive_entries = archive_entry_states(collection.ids())
                archive_tree_restored = False
                workspace_archive_path = util.path(clone_path, "DH1", "WHD")
                if workspace_state.get("archive_tree_cache_key") == archive_tree_cache_key and util.is_dir(workspace_archive_path):
                    archive_tree_restored = True
                    print(" > Reusing cached archive workspace")
                elif try_append_archives(clone_path, list(collection.ids()), current_archive_entries, workspace_state):
                    archive_tree_restored = True
                    workspace_state["appended_workspace"] = True
                else:
                    # Invalidate before replacing the staged tree.
                    workspace_state.pop("archive_entries", None)
                    workspace_state.pop("archive_tree_cache_key", None)
                    save_workspace_state(clone_path, workspace_state)
                    util.rm_path(workspace_archive_path)
                    print(" > Checking cached archive tree...")
                    with timed_step(timings, "archive tree restore"):
                        archive_tree_restored = restore_archive_tree_cache(archive_tree_cache_key, clone_path)
                    if archive_tree_restored:
                        print(" > Using cached archive tree")
                    else:
                        print(" > Rebuilding archive tree...")
                        extract_entries(clone_path, collection.ids(), verbose=True)
                        print(" > Saving cached archive tree...")
                        with timed_step(timings, "archive tree save"):
                            save_archive_tree_cache(archive_tree_cache_key, clone_path)
                workspace_state["archive_tree_cache_key"] = archive_tree_cache_key
                workspace_state["archive_entries"] = current_archive_entries
                workspace_state["archive_behavior"] = ARCHIVE_TREE_BEHAVIOR_FINGERPRINT
                archive_extract_cache_keys = get_archive_extract_cache_keys(collection.ids())

        layers = []

        # copy layers
        with timed_step(timings, "copy layers"):
            print("Adding layers...")
            layers_path = util.path(config_dir, config_base_name) + ".layers.yaml"
            if util.is_file(layers_path):
                layers = util.yaml_load(layers_path)
                if not isinstance(layers, list):
                    raise ValueError("layers definition not a list ({})".format(layers_path))
                for layer in layers:
                    if not (isinstance(layer, dict) and len(layer.keys()) == 1):
                        raise ValueError("layer definition malformed: {}".format(layer))
                    for src, dst in layer.items():
                        src_dir = util.path(config_dir, src)
                        if not util.is_dir(src_dir):
                            raise IOError("layer source not a directory ({})".format(src_dir))
                        if not (isinstance(dst, str) and dst[0] == "/"):
                            raise ValueError("layer destination malformed: ({})".format(dst))
                        print(" > '{}' -> '{}'".format(src, dst))
                        util.clone_tree(src_dir, util.path(clone_path, dst[1:]))

        # copy additional directories
        if not args.only_ags_tree and args.add_dirs:
            with timed_step(timings, "copy extra dirs"):
                print("Copying additional directories...")
                add_dirs_cache_state = get_add_dirs_cache_state(args.add_dirs)
                add_dirs_destinations = get_add_dirs_destinations(args.add_dirs)
                if workspace_state.get("add_dirs_cache_state") == add_dirs_cache_state and all(
                    util.is_dir(util.path(clone_path, dst.replace(":", "/"))) for dst in add_dirs_destinations
                ):
                    print(" > Reusing staged extra directories")
                    for s in args.add_dirs:
                        src_dir, dst = s.split("::", 1)
                        remove_ignored_host_files(util.path(clone_path, dst.replace(":", "/")))
                        print(" > '{}' -> '{}'".format(src_dir, dst))
                        print_add_dir_progress(src_dir, True)
                else:
                    for dst in workspace_state.get("add_dirs_destinations", []):
                        util.rm_path(util.path(clone_path, dst.replace(":", "/")))
                    for s in args.add_dirs:
                        d = s.split("::")
                        if len(d) != 2:
                            raise ValueError("--add-dir parameter malformed ({})".format(s))
                        elif util.is_dir(d[0]):
                            dest = util.path(clone_path, d[1].replace(":", "/"))
                            util.rm_path(dest)
                            print(" > '{}' -> '{}'".format(d[0], d[1]))
                            copy_add_dir_with_progress(d[0], dest, True)
                            remove_ignored_host_files(dest)
                        else:
                            raise IOError("--add-dir source not found ({})".format(d[0]))
                    workspace_state["add_dirs_cache_state"] = add_dirs_cache_state
                    workspace_state["add_dirs_destinations"] = add_dirs_destinations

        # Generate after layers so the option covers the final menu filenames.
        if args.chipset_profile == 'ecs':
            from ags_ecs import prepare_menu
            prepare_menu(amiga_ags_path)
        make_nsfw_option(db, amiga_ags_path, collection)

        # create directory caches
        with timed_step(timings, "build dir caches"):
            for path, dirs, files in os.walk(amiga_ags_path):
                cache = []

                cd_files = []
                cd_ranked = dict()
                for dir in util.sorted_natural(list(map(lambda n: n.removesuffix(".ags"), filter(lambda d: d.endswith(".ags"), dirs)))):
                    dirname = "{}/{}.ags".format(path, dir)
                    if dirname in collection.path_sort_rank:
                        cd_ranked["D{}".format(dir)] = collection.path_sort_rank[dirname]
                    else:
                        cd_files.append("D{}".format(dir))
                cache += [k for k, _ in sorted(cd_ranked.items(), key=lambda a:a[1])] + cd_files

                cd_files = []
                cd_ranked = dict()
                for file in util.sorted_natural(list(map(lambda n: n.removesuffix(".run"), filter(lambda f: f.endswith(".run"), files)))):
                    filename = "{}/{}.run".format(path, file)
                    if filename in collection.path_sort_rank:
                        cd_ranked["F{}".format(file)] = collection.path_sort_rank[filename]
                    else:
                        cd_files.append("F{}".format(file))
                cache += [k for k, _ in sorted(cd_ranked.items(), key=lambda a:a[1])] + cd_files

                # A missing run file exits AGS; keep this action last at the root.
                if path == amiga_ags_path:
                    cache.append("F[ Exit to Workbench ]")

                if cache:
                    cachefile = "{}\n".format(len(cache))
                    for line in cache: cachefile += "{}\n".format(convert_filename_uae2a(line))
                    open(util.path(path, ".dir"), mode="w", encoding="latin-1", errors="replace").write(cachefile)

        with timed_step(timings, "build hi-res launcher"):
            if args.chipset_profile == 'ecs':
                from ags_ecs import install_launcher
                install_launcher(amiga_ags_path, collection)
                util.rm_path(util.path(amiga_data_path, 'AGS-HiRes'))
            else:
                build_or_reuse_hires_launcher(amiga_ags_path, util.path(amiga_data_path, "AGS-HiRes"), collection, workspace_state, append_delta, source_trees=hires_source_trees)

        # build PFS container
        if not args.only_ags_tree:
            with timed_step(timings, "build pfs image"):
                output_image = util.path(out_dir, config_base_name + ".hdf")
                if args.incremental:
                    prepare_plan(clone_path, output_image, None, config_base_name,
                                 util.path("data", "pfs3", "pfs3.bin"),
                                 image_size_bytes=args.image_size_bytes,
                                 boot_extra_bytes=args.boot_extra_bytes)
                    print(" > Reusing existing partition layout; capacity is checked during incremental comparison")
                else:
                    layer_sources = []
                    for layer in layers:
                        for src, dst in layer.items():
                            layer_sources.append((util.path(config_dir, src), dst))
                    pfs_cache_state = get_pfs_partition_cache_state(
                        base_hdf_state["base_hdf_cache_dir"],
                        menu_subtree_cache_keys,
                        autoentries_cache_key,
                        archive_tree_cache_key,
                        layer_sources,
                        args.add_dirs,
                    )
                    pfs_cache_state["image_size_bytes"] = args.image_size_bytes
                    pfs_cache_state["boot_extra_bytes"] = args.boot_extra_bytes
                    pfs_partition_cache_key = get_pfs_partition_cache_key(pfs_cache_state)
                    pfs_partitions = restore_pfs_partition_cache(pfs_partition_cache_key, workspace_state)
                    if pfs_partitions is None:
                        with timed_step(timings, "calculate pfs sizes"):
                            pfs_partitions = calculate_pfs_partitions(clone_path, args.image_size_bytes, args.boot_extra_bytes)
                        save_pfs_partition_cache(pfs_partition_cache_key, pfs_partitions, workspace_state)
                    else:
                        print(" > Using cached partition sizes")
                    Path(clone_path, PLAN_NAME).unlink(missing_ok=True)
                    build_pfs(output_image, clone_path, True, partitions=list(pfs_partitions))

        with timed_step(timings, "prune caches"):
            if not workspace_state.get("appended_workspace"):
                prune_build_caches(
                    base_hdf_state["base_hdf_cache_dir"],
                    ags2_cache_key,
                    menu_subtree_cache_keys,
                    autoentries_cache_key,
                    archive_tree_cache_key,
                    archive_extract_cache_keys,
                    pfs_partition_cache_key,
                )

        # set up cloner environment
        if not args.only_ags_tree:
            with timed_step(timings, "setup cloner"):
                cloner_adf = util.path("data", "cloner", "boot.adf")
                cloner_cfg = util.path("data", "cloner", "template.fs-uae")
                cloner_cfg_amiberry = util.path("data", "cloner", "template.uae")
                clone_script = util.path(os.path.dirname(args.config_file), config_base_name) + ".clonescript"
                if util.is_file(cloner_adf) and util.is_file(cloner_cfg) and util.is_file(cloner_cfg_amiberry) and util.is_file(clone_script):
                    print("Copying cloner config...")
                    output_hdf_path = util.path(out_dir, config_base_name + ".hdf")
                    target_hdf_link_path = util.path(clone_path, "target.hdf")
                    shutil.copyfile(cloner_adf, util.path(clone_path, "boot.adf"))
                    util.make_dir(os.path.dirname(target_hdf_link_path))
                    util.rm_path(target_hdf_link_path)
                    os.symlink(output_hdf_path, target_hdf_link_path)
                    # create fs-uae config from template
                    with open(cloner_cfg, 'r') as f:
                        cfg = f.read()
                        cfg = cfg.replace("<config_base_name>", config_base_name)
                        cfg = cfg.replace("$AGSTEMP", paths.tmp())
                        cfg = cfg.replace("$AGSDEST", util.path(os.getenv("AGSDEST")))
                        cfg = cfg.replace("$FSUAEROM", util.path(os.getenv("FSUAEROM")))
                        open(util.path(clone_path, "cfg.fs-uae"), mode="w").write(cfg)
                    # create amiberry config from template
                    with open(cloner_cfg_amiberry, 'r') as f:
                        cfg = f.read()
                        cfg = cfg.replace("<config_base_name>", config_base_name)
                        cfg = cfg.replace("$AGSCONTENT", util.path(os.getenv("AGSCONTENT")))
                        cfg = cfg.replace("$AGSTEMP", paths.tmp())
                        cfg = cfg.replace("$AGSDEST", util.path(os.getenv("AGSDEST")))
                        cfg = cfg.replace("$FSUAEROM", os.path.abspath(util.path(os.getenv("FSUAEROM"))))
                        open(util.path(clone_path, "cfg.uae"), mode="w").write(cfg)
                    # copy clone script and write fs-uae metadata
                    clone_script_output = util.path(clone_path, "clone")
                    shutil.copyfile(clone_script, clone_script_output)
                    open(util.path(clone_path, "clone.uaem"), mode="w").write("-s--rwed 2020-02-02 22:22:22.00")
                    if args.incremental:
                        # The updater generates its own script after comparison.
                        Path(clone_path, "clone-progress").unlink(missing_ok=True)
                    else:
                        progress_lines = make_clone_progress_lines(clone_path)
                        write_clone_progress(clone_path, progress_lines)
                        inject_clone_progress(clone_script_output, clone_path, progress_lines)
                else:
                    raise IOError("cloner config files not found ({}, {}, {}, {})".format(cloner_adf, cloner_cfg, cloner_cfg_amiberry, clone_script))

        # clean output directory
        with timed_step(timings, "cleanup temp tree"):
            # Incremental comparison filters host files in its existing payload walk.
            if not args.incremental or args.only_ags_tree:
                for r, _, f in os.walk(clone_path):
                    for name in f:
                        if name == ".DS_Store":
                            os.remove(util.path(r, name))

        # run post-build script
        post_build_sh_path = util.path(os.path.dirname(args.config_file), config_base_name) + ".sh"
        if util.is_file(post_build_sh_path):
            with timed_step(timings, "post-build script"):
                r = subprocess.call(["sh", post_build_sh_path])
                if r != 0: return r

        if current_append_inputs is not None:
            workspace_state["append_inputs"] = current_append_inputs
        save_workspace_state(clone_path, workspace_state)

        # done
        print_timing_summary(timings)
        print_collection_timing_summary(collection)
        return 0

    # except Exception as err:
    except IOError as err:
        print("IO error - {}".format(err))
        sys.exit(1)
    except ValueError as err:
        print("Value error - {}".format(err))
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
