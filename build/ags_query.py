#!/usr/bin/env python3

# AGSImager: Query entries and paths

import sys
from typing import Tuple

import ags_paths as paths
import ags_util as util

# -----------------------------------------------------------------------------

def get_entry_lookup_patterns(name: str) -> list[str]:
    return [
        "game--{}".format(name),
        "game--{}--{}".format(name, name),
        "game--{}files--{}files".format(name, name),
        "game--{}ntsc--{}ntsc".format(name, name),
        "game--{}2mb--{}2mb".format(name, name),
        "game--{}1mb--{}1mb".format(name, name),
        "game--{}512kb--{}512kb".format(name, name),
        "game--{}aga--{}aga".format(name, name),
        "game--{}image--{}image".format(name, name),
        "game--{}4disk--{}4disk".format(name, name),
        "game--{}3disk--{}3disk".format(name, name),
        "game--{}2disk--{}2disk".format(name, name),
        "demo--{}".format(name),
        "demo--{}--{}".format(name, name),
        "game-notwhdl--{}%".format(name),
        "demo-notwhdl--{}%".format(name),
        "mags-notwhdl--{}%".format(name),
        "game--{}%".format(name),
        "demo--{}%".format(name),
        "%--{}%".format(name),
        "%{}%".format(name),
    ]

def iter_matching_rows(db, name):
    if not name:
        return

    lowered = name.lower()
    row = db.cursor().execute('SELECT * FROM titles WHERE id = ?', (lowered,)).fetchone()
    seen_ids = set()
    if row:
        seen_ids.add(row["id"].lower())
        yield row

    for pattern in get_entry_lookup_patterns(lowered):
        rows = db.cursor().execute('SELECT * FROM titles WHERE id LIKE ?', (pattern,)).fetchall()
        for row in rows:
            row_id = row["id"].lower()
            if row_id in seen_ids:
                continue
            seen_ids.add(row_id)
            yield row

def row_has_missing_archive(row) -> bool:
    if not row:
        return False
    archive_path = row["archive_path"]
    return bool(archive_path and not util.is_file(util.path(paths.titles(), archive_path)))

def sanitize_entry(entry):
    if entry is None:
        return None
    entry = dict(entry)
    archive_path = entry.get("archive_path")
    if archive_path:
        arc_path = util.path(paths.titles(), archive_path)
        if not util.is_file(arc_path):
            return None
    if entry_is_notwhdl(entry):
        return entry
    if entry_is_valid(entry) and entry["slave_path"].find("/") > 0:
        entry["slave_dir"] = entry["slave_path"].split("/")[0]
        entry["slave_name"] = entry["slave_path"].split("/")[1]
        entry["slave_id"] = entry["slave_name"][:-6]
        return entry
    return None

def get_entry_by_id(db, entry_id):
    if not entry_id:
        return None
    row = db.cursor().execute('SELECT * FROM titles WHERE id = ?', (entry_id.lower(),)).fetchone()
    return sanitize_entry(row)

def get_missing_archive_entry_by_id(db, entry_id):
    if not entry_id:
        return None
    row = db.cursor().execute('SELECT * FROM titles WHERE id = ?', (entry_id.lower(),)).fetchone()
    if row_has_missing_archive(row):
        return dict(row)
    return None

def get_preferred_entry(db, entry):
    if not entry:
        return None
    return get_entry_by_id(db, entry.get("preferred_version"))

def get_preferred_entry_issue(db, entry):
    if not entry:
        return None

    preferred_id = (entry.get("preferred_version") or "").strip().lower()
    if not preferred_id:
        return None

    row = db.cursor().execute('SELECT * FROM titles WHERE id = ?', (preferred_id,)).fetchone()
    if row is None:
        return "preferred version {} does not exist".format(preferred_id)

    if row_has_missing_archive(row):
        return "preferred version {} is missing archive {}".format(preferred_id, row["archive_path"])

    preferred_version = (row["preferred_version"] or "").strip().lower()
    if preferred_version == entry.get("id", "").strip().lower():
        return "preferred version cycle between {} and {}".format(entry["id"], row["id"])

    if sanitize_entry(row) is None:
        return "preferred version {} is not launchable".format(preferred_id)

    return None

def get_entry(db, name):
    for row in iter_matching_rows(db, name):
        entry = sanitize_entry(row)
        if entry:
            return entry, get_preferred_entry(db, entry)
    return None, None

def get_missing_archive_entry(db, name):
    for row in iter_matching_rows(db, name):
        if row_has_missing_archive(row):
            return dict(row)
    return None

def entry_is_valid(entry):
    if not (isinstance(entry, dict)): return False
    if not ("id" in entry and entry["id"]): return False
    if not ("title" in entry and entry["title"]): return False
    if not ("archive_path" in entry and entry["archive_path"]): return False
    if "slave_path" in entry and entry["slave_path"]:
        return True
    elif "game-notwhdl--" in entry["id"] or "demo-notwhdl--" in entry["id"] or "mags-notwhdl--" in entry["id"]:
        return True
    return False

def entry_is_aga(entry):
    if entry_is_valid(entry) and entry.get("aga", 0) > 0:
        return True
    return False

def entry_is_notwhdl(entry):
    if entry_is_valid(entry) and "game-notwhdl--" in entry["id"]:
        return True
    if entry_is_valid(entry) and "demo-notwhdl--" in entry["id"]:
        return True
    if entry_is_valid(entry) and "mags-notwhdl--" in entry["id"]:
        return True
    return False

def name_is_fuzzy(name):
    return not "--" in name

def has_english_language(entry):
    return "english" in entry.get("language", "").lower()

def get_languages(entry):
    return list(filter(None, entry.get("language", "").split(", ")))

def get_countries(entry):
    return list(filter(None, entry.get("country", "").split(", ")))

def get_publishers(entry):
    return list(filter(None, entry.get("publisher", "").split(", ")))

def get_hardware_short(entry) -> str:
    hardware = entry.get("hardware", "")
    if hardware:
        return hardware.replace("/ECS", "").replace("AGA/CD32", "CD32").replace("OCS/CDTV", "CDTV").replace("/", "-")
    else:
        return ""

def get_runscript_paths(entry) -> Tuple[str | None, str | None]:
    if not (isinstance(entry, dict)):
        return (None, None)
    if entry.get("issues"):
        return (util.path("Run", "Issues"), None)
    elif entry.get("category", "").lower() == "game":
        return (util.path("Run", "Game"), util.path("RunQuiet", "Game"))
    elif entry.get("category", "").lower() == "demo":
        sub = entry.get("subcategory", "").lower()
        if sub.startswith("music disk"):
            return (util.path("Run", "MusicDisk"), None)
        elif sub.startswith("disk mag"):
            return (util.path("Run", "DiskMag"), None)
        elif sub.startswith("slide"):
            return (util.path("Run", "Demo"), None)
        elif sub.startswith("demo") or sub.startswith("intro") or sub.startswith("crack"):
            return (util.path("Run", "Demo"), util.path("RunQuiet", "Demo"))
        else:
            return (util.path("Run", "Demo"), None)
    else:
        return (util.path("Run", "Misc"), None)

def get_whd_slavename(entry):
    if entry_is_valid(entry):
        name = entry["slave_name"]
        return name
    else:
        return None

def get_archive_path(entry):
    if entry_is_valid(entry):
        arc_path = util.path(paths.titles(), entry["archive_path"])
        return arc_path if util.is_file(arc_path) else None
    else:
        return None

def get_short_slavename(name):
    excess = len(name) - 30
    if excess > 0:
        parts = name.split(".")
        if len(parts) == 2 and parts[1].lower() == "slave":
            parts[0] = parts[0][:-excess]
            return ".".join(parts)
    return name

def get_whd_dir(clone_path, entry):
    if entry_is_notwhdl(entry):
        return util.path(clone_path, "DH1", "WHD", "N")
    else:
        p = "0-9" if entry["slave_dir"][0].isnumeric() else entry["slave_dir"][0].upper()
        if entry["id"].startswith("demo--"):
            return util.path(clone_path, "DH1", "WHD", "D", p)
        if entry["id"].startswith("mags--"):
            return util.path(clone_path, "DH1", "WHD", "M", p)
        else:
            return util.path(clone_path, "DH1", "WHD", "G", p)

def get_amiga_whd_dir(entry):
    if not entry_is_valid(entry):
        return None
    elif entry_is_notwhdl(entry):
        return None
    else:
        p = "0-9" if entry["slave_dir"][0].isnumeric() else entry["slave_dir"][0].upper()
        if entry["id"].startswith("demo--"):
            return "D/" + p + "/" + entry["slave_dir"]
        elif entry["id"].startswith("mags--"):
            return "M/" + p + "/" + entry["slave_dir"]
        else:
            return "G/" + p + "/" + entry["slave_dir"]

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("not runnable")
    sys.exit(1)
