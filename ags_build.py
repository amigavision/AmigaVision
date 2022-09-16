#!/usr/bin/env python3

# AGSImager: Builder

import argparse
import json
import operator
import os
import shutil
from sqlite3 import Connection
import sys
import textwrap

import ags_util as util
import ags_paths as paths
import ags_fs as fs
from make_vadjust import make_vadjust, VADJUST_MIN, VADJUST_MAX

# -----------------------------------------------------------------------------

AGS_LIST_WIDTH = 26
AGS_INFO_WIDTH = 48

class CollectedEntries:
    def __init__(self):
        # entry_id: entry
        self.by_id = dict()
        # {"entry_id", "path"}
        self.path_ids = set()
        # runfile_path: int
        self.path_sort_rank = dict()

    def ids(self):
        return self.by_id.values()

# -----------------------------------------------------------------------------
# Database and path queries

def get_entry(db, name):
    def sanitize(entry):
        if entry is None:
            return None
        entry = dict(entry)
        if entry_is_notwhdl(entry):
            return entry
        if entry_valid(entry) and entry["slave_path"].find("/") > 0:
            entry["slave_dir"] = entry["slave_path"].split("/")[0]
            entry["slave_name"] = entry["slave_path"].split("/")[1]
            entry["slave_id"] = entry["slave_name"][:-6]
            return entry
        return None

    n = name.lower()
    patterns = [
        "{}".format(n),
        "game--{}".format(n),
        "game--{}--{}".format(n, n),
        "game--{}ntsc--{}ntsc".format(n, n),
        "game--{}2mb--{}2mb".format(n, n),
        "game--{}1mb--{}1mb".format(n, n),
        "game--{}512kb--{}512kb".format(n, n),
        "game--{}aga--{}aga".format(n, n),
        "game--{}image--{}image".format(n, n),
        "game--{}4disk--{}4disk".format(n, n),
        "game--{}3disk--{}3disk".format(n, n),
        "game--{}2disk--{}2disk".format(n, n),
        "demo--{}".format(n),
        "demo--{}--{}".format(n, n),
        "game-notwhdl--{}%".format(n),
        "demo-notwhdl--{}%".format(n),
        "mags-notwhdl--{}%".format(n),
        "game--{}%".format(n),
        "demo--{}%".format(n),
        "%--{}%".format(n),
        "%{}%".format(n)
    ]
    for p in patterns:
        e = db.cursor().execute('SELECT * FROM titles WHERE id LIKE ?', (p.lower(),)).fetchone()
        entry = sanitize(e)
        if entry:
            preferred_entry = get_entry(db, entry["preferred_version"]) if "preferred_version" in entry and entry["preferred_version"] else None
            if preferred_entry:
                preferred_entry = preferred_entry[0]
            return entry, preferred_entry
    return None, None

def entry_valid(entry):
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
    print("is_aga:", entry)
    if entry_valid(entry) and entry.get("aga", 0) > 0:
        print(" > yes")
        return True
    return False

def entry_is_notwhdl(entry):
    if entry_valid(entry) and "game-notwhdl--" in entry["id"]:
        return True
    if entry_valid(entry) and "demo-notwhdl--" in entry["id"]:
        return True
    if entry_valid(entry) and "mags-notwhdl--" in entry["id"]:
        return True
    return False

def get_whd_slavename(entry):
    if entry_valid(entry):
        name = entry["slave_name"]
        return name
    else:
        return None

def get_archive_path(entry):
    if entry_valid(entry):
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
    if not entry_valid(entry):
        return None
    elif entry_is_notwhdl(entry):
        return None
    else:
        p = "0-9" if entry["slave_dir"][0].isnumeric() else entry["slave_dir"][0].upper()
        if entry["id"].startswith("demo--"):
            return "WHD:D/" + p + "/" + entry["slave_dir"]
        elif entry["id"].startswith("mags--"):
            return "WHD:M/" + p + "/" + entry["slave_dir"]
        else:
            return "WHD:G/" + p + "/" + entry["slave_dir"]

def extract_entries(clone_path, entries):
    unarchived = set()
    for entry in entries:
        if "archive_path" in entry and not entry["archive_path"] in unarchived:
            extract_whd(clone_path, entry)
            unarchived.add(entry["archive_path"])

def extract_whd(clone_path, entry):
    arc_path = get_archive_path(entry)
    if not arc_path:
        print(" > WARNING: content archive not found:", entry["id"])
    else:
        dest = get_whd_dir(clone_path, entry)
        if entry_is_notwhdl(entry):
            util.lha_extract(arc_path, dest)
        else:
            util.lha_extract(arc_path, dest)
            info_path = util.path(dest, entry["slave_dir"] + ".info")
            if util.is_file(info_path):
                os.remove(info_path)

def create_vadjust_dats(path):
    util.make_dir(path)
    for i in range(VADJUST_MIN, VADJUST_MAX+1):
        open(util.path(path, "xd_{}".format(i)), mode="wb").write(make_vadjust(i))
        open(util.path(path, "x5_{}".format(i)), mode="wb").write(make_vadjust(i, 5))
        open(util.path(path, "x6_{}".format(i)), mode="wb").write(make_vadjust(i, 6))

# -----------------------------------------------------------------------------
# Create entry and note

def ags_make_note(entry, add_note):
    max_w = AGS_INFO_WIDTH
    note = ""
    system = entry["hardware"].replace("/", "·")
    aspect_ratio = "40:27"

    # ntsc field options:
    #   0 = PAL title that will be run at 50Hz (PAL, 4:3@4X, 40:27@5X, 16:9@6X)
    #   1 = PAL title that will be run at 60Hz (PAL60, 40:27@5X, 16:9@6X)
    #   2 = "World" title that will be run at 60Hz (NTSC, 40:27@5X, 16:9@6X)
    #   3 = NTSC title that will be run at 60Hz (NTSC, 40:27@5X, 16:9@6X)
    #   4 = NTSC title that will be run at 60Hz and was likely designed for narrow PAR ("Sachs NTSC", 4:3@5X, 16:9@6X)
    if entry.get("ntsc", 0) == 4:
        if entry.get("scale", 0) == 6:
            system += "·6×NTSC"
            aspect_ratio = "16:9"
        else:
            system += "·5×NTSC"
            aspect_ratio = "4:3"
    elif entry.get("ntsc", 0) == 3:
        if entry.get("scale", 0) == 6:
            system += "·6×NTSC"
            aspect_ratio = "16:9"
        else:
            system += "·5×NTSC"
    elif entry.get("ntsc", 0) == 2:
        if entry.get("scale", 0) == 6:
            system += "·6×NTSC"
            aspect_ratio = "16:9"
        else:
            system += "·5×NTSC"
    elif entry.get("ntsc", 0) == 1:
        if entry.get("scale", 0) == 6:
            system += "·6×PAL60"
            aspect_ratio = "16:9"
        else:
            system += "·5×PAL60"
    else:
        if entry.get("scale", 0) == 6:
            system += "·6×PAL"
            aspect_ratio = "16:9"
        elif entry.get("scale", 0) == 5:
            system += "·5×PAL"
        else:
            system += "·4×PAL"
            aspect_ratio = "4:3"

    if entry.get("lightgun", False):
        system += "·Light Gun"
    elif entry.get("gamepad", False):
        system += "·Game Pad"
    system += " ({})".format(aspect_ratio)

    if "category" in entry and entry["category"].lower() == "game":
        note += ("Title:      {}".format(entry["title"]))[:max_w] + "\n"
        note += ("Developer:  {}".format(entry["developer"]))[:max_w] + "\n"
        note += ("Publisher:  {}".format(entry["publisher"]))[:max_w] + "\n"
        note += ("Released:   {}".format(entry["release_date"]))[:max_w] + "\n"
        note += ("Players:    {}".format(entry["players"]))[:max_w] + "\n"
        note += ("Hardware:   {}".format(system))[:max_w] + "\n"
        if entry.get("issues"):
            note += ("Issues:     {}".format(entry["issues"]))[:max_w] + "\n"
        elif entry.get("hack"):
            note += ("Hack Info:  {}".format(entry["hack"]))[:max_w] + "\n"

    elif "category" in entry and entry["category"].lower() == "demo":
        group = util.prettify_names(entry["publisher"])
        note += ("Title:      {}".format(entry["title"]))[:max_w] + "\n"
        note += ("Group:      {}".format(group))[:max_w] + "\n"
        if entry.get("country"):
            note += ("Country:    {}".format(entry["country"]))[:max_w] + "\n"
        note += ("Released:   {}".format(entry["release_date"]))[:max_w] + "\n"
        if entry.get("subcategory", "").lower() != "demo":
            note += ("Category:   {}".format(entry["subcategory"]))[:max_w] + "\n"
        else:
            note += "Category:   Demo\n"
        note += ("Hardware:   {}".format(system))[:max_w] + "\n"
        if entry.get("issues"):
            note += ("Issues:     {}".format(entry["issues"]))[:max_w] + "\n"

    if add_note and isinstance(add_note, str):
            note += ("Note:       {}".format(add_note))[:max_w] + "\n"
    elif entry.get("note"):
            note += ("Note:       {}".format(entry["note"]))[:max_w] + "\n"
    return note

def ags_fix_filename(name):
    name = name.replace("/", "-").replace("\\", "-").replace(": ", " ").replace(":", " ")
    name = name.replace(" [AGA]", "")
    if name[0] == '(':
        name = name.replace('(', '[', 1).replace(')', ']', 1)
    return name


def ags_create_entry(entries: CollectedEntries, ags_path, name, entry, path, rank=None, only_script=False, prefix=None, options=None):
    max_w = AGS_LIST_WIDTH
    note = None
    runfile_ext = "" if only_script else ".run"

    # apply override options
    if isinstance(options, dict):
        if entry and isinstance(entry, dict):
            entry.update(options)
        elif "note" in options and isinstance(options["note"], str):
            note = options["note"]

    if isinstance(entry, dict) and isinstance(entry["note"], str):
        note = entry["note"]

    # skip if entry already added at path
    path_id = json.dumps({"entry_id": entry["id"] if (entry and entry["id"]) else name, "path": path})
    if path_id in entries.path_ids:
        return
    else:
        entries.path_ids.add(path_id)

    # fix path name
    path_prefix = ags_path
    if path != path_prefix:
        path_suffix = path.split(path_prefix + "/")[-1]
        path = path_prefix + "/" + "/".join(list(map(ags_fix_filename, path_suffix.split("/"))))

    # base name
    title = rank + ". " if rank else ""
    if prefix:
        title = prefix + " - " + title

    if options and options.get("unavailable", False):
        title += ags_fix_filename(name.replace("-", " "))
    elif entry and "title_short" in entry:
        if only_script:
            title = ags_fix_filename(entry["title_short"]).replace(" ", "_")
        else:
            title += ags_fix_filename(entry["title_short"])
            if len(title) > max_w: title = title.replace(", The", "")
    else:
        title += name

    # prevent name clash
    title = title.strip()
    if util.is_file(util.path(path, title) + runfile_ext):
        if entry.get("category", "").lower() == "demo":
            title += " (" + entry.get("publisher") + ")"
        else:
            title += " (" + entry.get("hardware", "").replace("/ECS", "").replace("AGA/CD32", "CD32").replace("OCS/CDTV", "CDTV").replace("/", "-") + ")"
        if only_script:
            title = title.replace(" ", "_")
    if not only_script and len(title) > max_w:
        title = title[:max_w - 2].strip() + ".."
        if util.is_file(util.path(path, title) + runfile_ext):
            suffix = 1
            while suffix <= 10:
                title = title[:-1] + str(suffix)
                suffix += 1
                if not util.is_file(util.path(path, title) + runfile_ext):
                    break

    base_path = util.path(path, title)
    util.make_dir(path)

    # create runfile
    runfile = None
    if get_amiga_whd_dir(entry) is not None or entry_is_notwhdl(entry):
        # videomode
        whd_vmode = "NTSC" if util.parse_int(entry.get("ntsc", 0)) > 0 else "PAL"
        # vadjust
        vadjust_scale = util.parse_int(entry.get("scale", 0))
        if not vadjust_scale: vadjust_scale = 0
        vadjust_vofs = util.parse_int(entry.get("v_offset", 0))
        if not vadjust_vofs: vadjust_vofs = 0
        vadjust_vofs = min(max(vadjust_vofs, VADJUST_MIN), VADJUST_MAX)

        if entry_is_notwhdl(entry):
            runfile_source_path = get_archive_path(entry).replace(".lha", ".run")
            if util.is_file(runfile_source_path):
                runfile = "ags_notify TITLE=\"{}\"\n".format(entry.get("title", "Unknown"))
                runfile += "set{}\n".format(whd_vmode.lower())
                runfile += "setvadjust {} {}\n".format(vadjust_vofs, vadjust_scale)
                with open(runfile_source_path, 'r') as f: runfile += f.read()
                runfile += "setvmode $AGSVMode\n"
                runfile += "setvadjust\n"
                runfile += "ags_notify\n"
        else:
            whd_entrypath = get_amiga_whd_dir(entry)
            if whd_entrypath:
                whd_slave = get_whd_slavename(entry)
                # extra arguments
                whd_cargs = "BUTTONWAIT"
                if entry.get("slave_args"):
                    whd_cargs += " " + entry["slave_args"]
                whd_qtkey = "" if "QuitKey=" in whd_cargs else "$whdlqtkey"
                runfile = "ags_notify TITLE=\"{}\"\n".format(entry.get("title", "Unknown"))
                runfile += "cd \"{}\"\n".format(whd_entrypath)
                runfile += "IF NOT EXISTS ENV:whdlspdly\n"
                runfile += "  echo 200 >ENV:whdlspdly\n"
                runfile += "ENDIF\n"
                runfile += "IF NOT EXISTS ENV:whdlqtkey\n"
                runfile += "  echo \"\" >ENV:whdlqtkey\n"
                runfile += "ENDIF\n"
                runfile += "IF EXISTS ENV:whdlvmode\n"
                runfile += "  whdload >NIL: \"{}\" $whdlvmode {} SplashDelay=$whdlspdly {}\n".format(whd_slave, whd_cargs, whd_qtkey)
                runfile += "ELSE\n"
                runfile += "  setvadjust {} {}\n".format(vadjust_vofs, vadjust_scale)
                if only_script:
                    runfile += "  whdload >NIL: \"{}\" {} {} SplashDelay=0 {}\n".format(whd_slave, whd_vmode, whd_cargs, whd_qtkey)
                else:
                    runfile += "  whdload >NIL: \"{}\" {} {} SplashDelay=$whdlspdly {}\n".format(whd_slave, whd_vmode, whd_cargs, whd_qtkey)
                runfile += "  setvadjust\n"
                runfile += "ENDIF\n"
                runfile += "ags_notify\n"
    else:
        runfile = "echo \"Title not available.\"" + "\n" + "wait 2"

    if runfile:
        runfile_dest_path = base_path + runfile_ext
        if util.is_file(runfile_dest_path):
            print(" > AGS2 clash:", entry["id"], "-", runfile_dest_path)
        else:
            open(runfile_dest_path, mode="w", encoding="latin-1").write(runfile)

    if only_script:
        return None

    # note
    if options and options.get("unavailable", False):
        note = "Title:      " + name.replace("-", " ") + "\n\n"
        note += "Content is unavailable."
        open(base_path + ".txt", mode="w", encoding="latin-1").write(note)
    elif entry:
        open(base_path + ".txt", mode="w", encoding="latin-1").write(ags_make_note(entry, note))

    # image
    if entry and "id" in entry and util.is_file(util.path("data", "img", entry["id"] + ".iff")):
        shutil.copyfile(util.path("data", "img", entry["id"] + ".iff"), base_path + ".iff")
    return base_path

# -----------------------------------------------------------------------------
# Create entries from list

def ags_create_entries(db: Connection, collected_entries: CollectedEntries, ags_path, entries, path, note=None, ranked_list=False):
    # make dir
    base_path = ags_path
    if path:
        for d in path:
            base_path = util.path(base_path, d[:26].strip() + ".ags")
    util.make_dir(base_path)

    # make note
    if note:
        note = "\n".join([textwrap.fill(p, AGS_INFO_WIDTH) for p in note.replace("\\n", "\n").splitlines()])
        open(base_path[:-4] + ".txt", mode="w", encoding="latin-1").write(note)

    # collect titles
    pos = 0
    for name in entries:
        pos += 1
        n = name
        options = None
        if isinstance(name, tuple) and len(name) == 2 and isinstance(name[1], dict):
            n = name[0]
            options = name[1]

        # use preferred (fuzzy) entry
        e, pe = get_entry(db, n)
        if not "--" in name and pe:
            e = pe
        if not e and not pe:
            if options is None or (options and not options.get("unavailable", False)):
                print(" > WARNING: invalid entry: {}".format(n))
        else:
            collected_entries.by_id[e["id"]] = e
        rank = None
        if ranked_list:
            rank = str(pos).zfill(len(str(len(entries))))
        ags_create_entry(collected_entries, ags_path, n, e, base_path, rank=rank, options=options)
    return

# -----------------------------------------------------------------------------
# Collect entries for special folders "All Games" and "Demo Scene"

def ags_create_autoentries(entries: CollectedEntries, path, all_games=False, all_demos=False):
    dir_allgames = "[ All Games ]"
    dir_allgames_year = "[ All Games, by year ]"
    dir_scene = "[ Demo Scene ]"
    dir_demos = "[ Demos by title ]"
    dir_demos_country = "[ Demos by country ]"
    dir_demos_group = "[ Demos by group ]"
    dir_demos_year = "[ Demos by year ]"
    dir_demos_cracktro = "[ Demos, crack intros ]"
    dir_demos_intro = "[ Demos, 1-64KB ]"
    dir_diskmags = "[ Disk Magazines ]"
    dir_diskmags_date = "[ Disk Magazines by date ]"
    dir_musicdisks = "[ Music Disks by title ]"
    dir_musicdisks_year = "[ Music Disks by year ]"
    dir_issues = "[ Issues ]"

    if all_demos:
        d_path = util.path(path, "{}.ags".format(dir_scene))
        util.make_dir(d_path)

    for entry in sorted(entries.ids(), key=operator.itemgetter("title")):
        letter = entry.get("title_short", "z")[0].upper()
        if letter.isnumeric():
            letter = "0-9"
        year, _, _ = util.parse_date(entry["release_date"])
        if "x" in year.lower():
            year = "Unknown"

        # Demos / Music Disks / Disk Mags
        def add_demo(entry, sort_group, sort_country):
            if sort_group.startswith("The "):
                sort_group = sort_group[4:]
            sort_group = sort_group[:AGS_LIST_WIDTH]
            group_letter = sort_group[0].upper()
            if group_letter.isnumeric():
                group_letter = "0-9"
            if entry.get("subcategory", "").lower().startswith("disk mag"):
                ags_create_entry(entries, path, None, entry, util.path(d_path, "{}.ags".format(dir_diskmags)))
                mag_path = ags_create_entry(entries, path, None, entry, util.path(d_path, "{}.ags".format(dir_diskmags_date)))
                if mag_path:
                    rank = util.parse_date_int(entry["release_date"], sortable=True)
                    entries.path_sort_rank["{}.run".format(mag_path)] = rank if rank else 0
            elif entry.get("subcategory", "").lower().startswith("music disk"):
                ags_create_entry(entries, path, None, entry, util.path(d_path, "{}.ags".format(dir_musicdisks), letter + ".ags"))
                ags_create_entry(entries, path, None, entry, util.path(d_path, "{}.ags".format(dir_musicdisks_year), year + ".ags"))
            else:
                if entry.get("subcategory", "").lower().startswith("crack"):
                    ags_create_entry(entries, path, None, entry, util.path(d_path, "{}.ags".format(dir_demos_cracktro)), prefix=sort_group)
                if entry.get("subcategory", "").lower().startswith("intro"):
                    ags_create_entry(entries, path, None, entry, util.path(d_path, "{}.ags".format(dir_demos_intro)))
                group_entry = dict(entry)
                group_entry["title_short"] = group_entry.get("title")
                ags_create_entry(entries, path, None, entry, util.path(d_path, "{}.ags".format(dir_demos), letter + ".ags"))
                ags_create_entry(entries, path, None, group_entry, util.path(d_path, "{}.ags".format(dir_demos_group), group_letter + ".ags"), prefix=sort_group)
                ags_create_entry(entries, path, None, entry, util.path(d_path, "{}.ags".format(dir_demos_year), year + ".ags"))
                if sort_country:
                    ags_create_entry(entries, path, None, entry, util.path(d_path, "{}.ags".format(dir_demos_country), sort_country + ".ags"))

        if all_games and entry.get("category", "").lower() == "game":
            ags_create_entry(entries, path, None, entry, util.path(path, "{}.ags".format(dir_allgames), letter + ".ags"))
            ags_create_entry(entries, path, None, entry, util.path(path, "{}.ags".format(dir_allgames_year), year + ".ags"))

        if all_demos and entry.get("category", "").lower() == "demo":
            groups = entry.get("publisher")
            if not groups:
                continue
            for sort_group in groups.split(", "):
                countries = entry.get("country")
                if not countries:
                    add_demo(entry, sort_group, None)
                else:
                    for sort_country in countries.split(", "):
                        add_demo(entry, sort_group, sort_country)

        # Run-scripts for randomizer
        if all_games and entry.get("category", "").lower() == "game" and not entry.get("issues"):
            ags_create_entry(entries, path, None, entry, util.path(path, "Run", "Game"), only_script=True)
        elif all_demos and entry.get("category", "").lower() == "demo" and not entry.get("issues"):
            sub = entry.get("subcategory", "").lower()
            if sub.startswith("demo") or sub.startswith("intro") or sub.startswith("crack"):
                ags_create_entry(entries, path, None, entry, util.path(path, "Run", "Demo"), only_script=True)

    # Notes for created directories
    if util.is_dir(util.path(path, "{}.ags".format(dir_allgames))):
        open(util.path(path, "{}.txt".format(dir_allgames)), mode="w", encoding="latin-1").write("Browse all games alphabetically.")
    if util.is_dir(util.path(path, "{}.ags".format(dir_allgames_year))):
        open(util.path(path, "{}.txt".format(dir_allgames_year)), mode="w", encoding="latin-1").write("Browse all games by release year.")

    if all_demos:
        if util.is_dir(util.path(d_path, "{}.ags".format(dir_demos_group))):
            open(util.path(d_path, "{}.txt".format(dir_demos_group)), mode="w", encoding="latin-1").write("Browse demos by release group.")
        if util.is_dir(util.path(d_path, "{}.ags".format(dir_demos_country))):
            open(util.path(d_path, "{}.txt".format(dir_demos_country)), mode="w", encoding="latin-1").write("Browse demos by country of origin.")
        if util.is_dir(util.path(d_path, "{}.ags".format(dir_demos))):
            open(util.path(d_path, "{}.txt".format(dir_demos)), mode="w", encoding="latin-1").write("Browse demos by title.")
        if util.is_dir(util.path(d_path, "{}.ags".format(dir_demos_year))):
            open(util.path(d_path, "{}.txt".format(dir_demos_year)), mode="w", encoding="latin-1").write("Browse demos by release year.")
        if util.is_dir(util.path(d_path, "{}.ags".format(dir_demos_intro))):
            open(util.path(d_path, "{}.txt".format(dir_demos_intro)), mode="w", encoding="latin-1").write("Browse demos in the 1/4/40/64KB categories.")
        if util.is_dir(util.path(d_path, "{}.ags".format(dir_demos_cracktro))):
            open(util.path(d_path, "{}.txt".format(dir_demos_cracktro)), mode="w", encoding="latin-1").write("A glimpse into the origins of the demo scene.")
        if util.is_dir(util.path(d_path, "{}.ags".format(dir_diskmags))):
            open(util.path(d_path, "{}.txt".format(dir_diskmags)), mode="w", encoding="latin-1").write("A selection of scene disk magazines.")
        if util.is_dir(util.path(d_path, "{}.ags".format(dir_diskmags_date))):
            open(util.path(d_path, "{}.txt".format(dir_diskmags_date)), mode="w", encoding="latin-1").write("Disk magazines in chronological order.")
        if util.is_dir(util.path(d_path, "{}.ags".format(dir_musicdisks))):
            open(util.path(d_path, "{}.txt".format(dir_musicdisks)), mode="w", encoding="latin-1").write("Browse music disks by title.")
        if util.is_dir(util.path(d_path, "{}.ags".format(dir_musicdisks_year))):
            open(util.path(d_path, "{}.txt".format(dir_musicdisks_year)), mode="w", encoding="latin-1").write("Browse music disks by year.")

    if util.is_dir(util.path(path, "{}.ags".format(dir_issues))):
        open(util.path(path, "{}.txt".format(dir_issues)), mode="w", encoding="latin-1").write(
            "Titles with known issues on Minimig_MiSTer.\n(Please report any new or resolved issues!)")

# -----------------------------------------------------------------------------
# Menu yaml parsing, AGS2 tree creation

def ags_create_tree(db: Connection, collected_entries: CollectedEntries, ags_path, node, path=[]):
    if isinstance(node, list):
        entries = []
        note = None
        ranked_list = False

        for item in node:
            # plain titles
            if isinstance(item, str):
                entries += [item]
            if isinstance(item, list):
                if len(item) == 2:
                    entries += [(item[0], item[1])]
            # parse metadata or subtree
            if isinstance(item, dict):
                if "note" in item:
                    note = str(item["note"])
                    del item["note"]
                if "ranked_list" in item:
                    ranked_list = item["ranked_list"]
                    del item["ranked_list"]
                for key, value in item.items():
                    if isinstance(value, dict):
                        # item has override options
                        entries += [(key, value)]
                    else:
                        # item is a subtree
                        ags_create_tree(db, collected_entries, ags_path, value, path + [key])
        ags_create_entries(db, collected_entries, ags_path, entries, path, note=note, ranked_list=ranked_list)

def ags_add_all(db: Connection, entries: CollectedEntries, category, all_versions, prefer_ecs):
    for r in db.cursor().execute('SELECT * FROM titles WHERE category=? AND (redundant IS NULL OR redundant="")', (category,)):
        entry, preferred_entry = get_entry(db, r["id"])
        if entry:
            if all_versions:
                entries.by_id[entry["id"]] = entry
            elif prefer_ecs is False:
                if preferred_entry:
                    entries.by_id[preferred_entry["id"]] = preferred_entry
                else:
                    entries.by_id[entry["id"]] = entry
            else:
                if entry_is_aga(entry):
                    continue
                if preferred_entry and entry_is_aga(preferred_entry):
                    entries.by_id[entry["id"]] = entry
                elif preferred_entry:
                    entries.by_id[preferred_entry["id"]] = preferred_entry
                else:
                    entries.by_id[entry["id"]] = entry

# -----------------------------------------------------------------------------
# command line interface

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", dest="config_file", required=True, metavar="FILE", type=lambda x: util.argparse_is_file(parser, x),  help="configuration file")
    parser.add_argument("-o", "--out_dir", dest="out_dir", metavar="FILE", type=lambda x: util.argparse_is_dir(parser, x),  help="output directory")
    parser.add_argument("-b", "--base_hdf", dest="base_hdf", metavar="FILE", help="base HDF image")
    parser.add_argument("-a", "--ags_dir", dest="ags_dir", metavar="FILE", type=lambda x: util.argparse_is_dir(parser, x),  help="AGS2 configuration directory")
    parser.add_argument("-d", "--add_dir", dest="add_dirs", action="append", help="add dir to amiga filesystem (example 'DH1:Music::~/Amiga/Music')")

    parser.add_argument("--all_games", dest="all_games", action="store_true", default=False, help="include all games in database")
    parser.add_argument("--all_demos", dest="all_demos", action="store_true", default=False, help="include all demos in database")
    parser.add_argument("--all_versions", dest="all_versions", action="store_true", default=False, help="include all non-redundant versions of titles (if --all_games)")
    parser.add_argument("--prefer_ecs", dest="prefer_ecs", action="store_true", default=False, help="prefer OCS/ECS versions (if --all_games)")

    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", default=False, help="verbose output")

    try:
        paths.verify()
        args = parser.parse_args()

        db = util.get_db(args.verbose)
        collected_entries = CollectedEntries()

        if args.out_dir:
            out_dir = args.out_dir

        clone_path = util.path(out_dir, "tmp")
        amiga_boot_path = util.path(clone_path, "DH0")
        amiga_ags_path = util.path(amiga_boot_path, "AGS2")

        if util.is_dir(clone_path):
            shutil.rmtree(clone_path)
        util.make_dir(util.path(clone_path, "DH0"))

        config_base_name = os.path.splitext(os.path.basename(args.config_file))[0]

        data_dir = "data"
        if not util.is_dir(data_dir):
            raise IOError("data dir doesn't exist: " + data_dir)

        # extract base image
        base_hdf = args.base_hdf
        if not base_hdf:
            base_hdf = util.path(paths.content(), "base", "base.hdf")
        if not util.is_file(base_hdf):
            raise IOError("base HDF doesn't exist: " + base_hdf)
        if args.verbose: print("extracting base HDF image... ({})".format(base_hdf))
        fs.extract_base_image(base_hdf, amiga_boot_path)

        # parse menu
        menu = None
        if args.verbose: print("parsing menu...")
        menu = util.yaml_load(args.config_file)
        if not isinstance(menu, list):
            raise ValueError("config file not a list: " + args.config_file)

        # copy base AGS2 config, create database
        if args.verbose: print("building AGS2 database...")

        base_ags2 = args.ags_dir
        if not base_ags2:
            base_ags2 = util.path("data", "ags2")
        if not util.is_dir(base_ags2):
            raise IOError("AGS2 configuration directory doesn't exist: " + base_ags2)
        if args.verbose:
            print(" > using configuration: " + base_ags2)

        util.copytree(base_ags2, amiga_ags_path)

        # collect entries
        if menu:
            ags_create_tree(db, collected_entries, amiga_ags_path, menu)
        if args.all_games:
            ags_add_all(db, collected_entries, "Game", args.all_versions, args.prefer_ecs)
        if args.all_demos:
            ags_add_all(db, collected_entries, "Demo", args.all_versions, args.prefer_ecs)
        if args.all_games or args.all_demos:
            ags_create_autoentries(collected_entries, amiga_ags_path, args.all_games, args.all_demos)

        # extract whdloaders
        if args.verbose: print("extracting {} content archives...".format(len(collected_entries.by_id.items())))
        extract_entries(clone_path, collected_entries.ids())

        create_vadjust_dats(util.path(amiga_boot_path, "S", "vadjust_dat"))

        # copy extra files
        config_extra_dir = util.path(os.path.dirname(args.config_file), config_base_name)
        if util.is_dir(config_extra_dir):
            if args.verbose: print("copying configuration extras...")
            util.copytree(config_extra_dir, clone_path)

        # copy additional directories
        if args.add_dirs:
            if args.verbose: print("copying additional directories...")
            for s in args.add_dirs:
                d = s.split("::")
                if util.is_dir(d[0]):
                    dest = util.path(clone_path, d[1].replace(":", "/"))
                    print(" > copying '" + d[0] +"' to '" + d[1] + "'")
                    util.copytree(d[0], dest)
                else:
                    print(" > WARNING: '" + d[1] + "' doesn't exist")

        # create directory caches
        for path, dirs, files in os.walk(amiga_ags_path):
            cd_dirs = []
            cd_files = []
            cd_ranked = dict()
            for dir in util.sorted_natural(list(map(lambda n: n.removesuffix(".ags"), filter(lambda d: d.endswith(".ags"), dirs)))):
                cd_dirs.append("D{}".format(dir))
            for file in util.sorted_natural(list(map(lambda n: n.removesuffix(".run"), filter(lambda f: f.endswith(".run"), files)))):
                runfile = "{}/{}.run".format(path, file)
                if runfile in collected_entries.path_sort_rank:
                    cd_ranked["F{}".format(file)] = collected_entries.path_sort_rank[runfile]
                else:
                    cd_files.append("F{}".format(file))

            cd_ranked_list = []
            if len(cd_ranked) > 0:
                cd_ranked_list = [k for k, v in sorted(cd_ranked.items(), key=lambda a:a[1])]

            cache = cd_dirs + cd_ranked_list + cd_files
            if len(cache) > 0:
                cachefile = "{}\n".format(len(cache))
                for line in cache: cachefile += "{}\n".format(line)
                open(util.path(path, ".dir"), mode="w", encoding="latin-1").write(cachefile)

        # build PFS container
        fs.build_pfs(util.path(out_dir, config_base_name + ".hdf"), clone_path, args.verbose)

        # set up cloner environment
        cloner_adf = util.path("data", "cloner", "boot.adf")
        cloner_cfg = util.path("data", "cloner", "template.fs-uae")
        clone_script = util.path(os.path.dirname(args.config_file), config_base_name) + ".clonescript"
        if util.is_file(cloner_adf) and util.is_file(cloner_cfg) and util.is_file(clone_script):
            if args.verbose: print("copying cloner config...")
            shutil.copyfile(cloner_adf, util.path(clone_path, "boot.adf"))
            # create config from template
            with open(cloner_cfg, 'r') as f:
                cfg = f.read()
                cfg = cfg.replace("<config_base_name>", config_base_name)
                cfg = cfg.replace("$AGSTEMP", paths.tmp())
                cfg = cfg.replace("$AGSDEST", util.path(os.getenv("AGSDEST")))
                cfg = cfg.replace("$FSUAEROM", util.path(os.getenv("FSUAEROM")))
                open(util.path(clone_path, "cfg.fs-uae"), mode="w").write(cfg)
            # copy clone script and write fs-uae metadata
            shutil.copyfile(clone_script, util.path(clone_path, "clone"))
            open(util.path(clone_path, "clone.uaem"), mode="w").write("-s--rwed 2020-02-02 22:22:22.00")
        else:
            print("WARNING: cloner config files not found")

        # clean output directory
        for r, _, f in os.walk(clone_path):
            for name in f:
                path = util.path(r, name)
                if name == ".DS_Store":
                    os.remove(path)

        # create title listings
        list_dir = util.path(out_dir, "games", "Amiga", "listings")
        if util.is_dir(list_dir):
            shutil.rmtree(list_dir)
        util.make_dir(list_dir)
        for list_def in [("Game", "games.txt"), ("Demo", "demos.txt")]:
            content_path = util.path(amiga_ags_path, "Run", list_def[0])
            if util.is_dir(content_path):
                listing = "\n".join(sorted(os.listdir(util.path(amiga_ags_path, "Run", list_def[0])), key=str.casefold))
                open(util.path(list_dir, list_def[1]), mode="w", encoding="latin-1").write(listing)

        # done
        return 0

    # except Exception as err:
    except IOError as err:
        print("error - {}".format(err))
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
