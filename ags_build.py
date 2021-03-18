#!/usr/bin/env python3

# AGSImager: Builder

import argparse
import operator
import os
import shutil
import subprocess
import sys
import textwrap
from ast import literal_eval as make_tuple
import ags_util as util
import ags_paths as paths
from make_vadjust import make_vadjust

# -----------------------------------------------------------------------------

AGS_LIST_WIDTH = 26
AGS_INFO_WIDTH = 48
VADJUST_CREATE_RANGE = True

g_out_dir = "out"
g_clone_dir = None
g_args = None
g_db = None
g_entries = dict()
g_entry_for_path = set()
g_vadjust = dict()

# -----------------------------------------------------------------------------
# Database and path queries

def get_entry(name):
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
        e = g_db.cursor().execute('SELECT * FROM titles WHERE id LIKE ?', (p.lower(),)).fetchone()
        entry = sanitize(e)
        if entry:
            preferred_entry = get_entry(entry["preferred_version"]) if "preferred_version" in entry and entry["preferred_version"] else None
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
    if entry_valid(entry) and "aga" in entry and entry["aga"]:
        if int(entry["aga"]) > 0:
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

def is_amiga_devicename(str):
    return len(str) == 3 and str[0].isalpha() and str[1].isalpha() and str[2].isnumeric()

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

def get_boot_dir():
    return util.path(g_clone_dir, "DH0")

def get_games_dir():
    return util.path(g_clone_dir, "DH1")

def get_ags2_dir():
    return util.path(get_boot_dir(), "AGS2")

def get_whd_dir(entry):
    if entry_is_notwhdl(entry):
        return util.path(g_clone_dir, "DH1", "WHD", "N")
    else:
        p = "0-9" if entry["slave_dir"][0].isnumeric() else entry["slave_dir"][0].upper()
        if entry["id"].startswith("demo--"):
            return util.path(g_clone_dir, "DH1", "WHD", "D", p)
        if entry["id"].startswith("mags--"):
            return util.path(g_clone_dir, "DH1", "WHD", "M", p)
        else:
            return util.path(g_clone_dir, "DH1", "WHD", "G", p)

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

def extract_entries(entries):
    unarchived = set()
    for _, entry in entries.items():
        if "archive_path" in entry and not entry["archive_path"] in unarchived:
            extract_whd(entry)
            unarchived.add(entry["archive_path"])

def extract_whd(entry):
    arc_path = get_archive_path(entry)
    if not arc_path:
        print(" > WARNING: content archive not found:", entry["id"])
    else:
        dest = get_whd_dir(entry)
        if entry_is_notwhdl(entry):
            util.lha_extract(arc_path, dest)
        else:
            util.lha_extract(arc_path, dest)
            info_path = util.path(dest, entry["slave_dir"] + ".info")
            if util.is_file(info_path):
                os.remove(info_path)

def create_vadjust_dats(vadjust_dict):
    util.make_dir(util.path(get_ags2_dir(), "VAdjust"))
    if vadjust_dict:
        for name, settings in vadjust_dict.items():
            pal5 = settings[0]
            vofs = 0 if pal5 and settings[1] is None else settings[1]
            data = make_vadjust(pal5, vofs)
            open(util.path(get_ags2_dir(), "VAdjust", name), mode="wb").write(data)
    else:
        for i in range(-32,33):
            open(util.path(get_ags2_dir(), "VAdjust", "def_{}".format(i)), mode="wb").write(make_vadjust(False, i))
            open(util.path(get_ags2_dir(), "VAdjust", "pal5_{}".format(i)), mode="wb").write(make_vadjust(True, i))

# -----------------------------------------------------------------------------
# Menu yaml parsing, AGS2 tree creation

def ags_make_note(entry, add_note):
    max_w = AGS_INFO_WIDTH
    note = ""
    system = entry["hardware"]

    if entry["ntsc"] > 1: system += "/NTSC"
    elif entry["ntsc"] == 1: system += "/PAL60"
    else: system += "/PAL"

    peripherals = []
    if entry["gamepad"]: peripherals.append("gamepad")
    if entry["lightgun"]: peripherals.append("light gun")
    if peripherals:
        system += " (" + " ,".join(peripherals) + ")"

    if "category" in entry and entry["category"].lower() == "game":
        note += ("Title:      {}".format(entry["title"]))[:max_w] + "\n"
        note += ("Developer:  {}".format(entry["developer"]))[:max_w] + "\n"
        note += ("Publisher:  {}".format(entry["publisher"]))[:max_w] + "\n"
        note += ("Year:       {}".format(entry["year"]))[:max_w] + "\n"
        note += ("Players:    {}".format(entry["players"]))[:max_w] + "\n"
        note += ("Hardware:   {}".format(system))[:max_w] + "\n"
        if entry["issues"]:
            note += ("Issues:     {}".format(entry["issues"]))[:max_w] + "\n"
        elif entry["hack"]:
            note += ("Hack Info:  {}".format(entry["hack"]))[:max_w] + "\n"

    elif "category" in entry and entry["category"].lower() == "demo":
        group = util.prettify_names(entry["publisher"])
        note += ("Title:      {}".format(entry["title"]))[:max_w] + "\n"
        note += ("Group:      {}".format(group))[:max_w] + "\n"
        if entry["country"]:
            note += ("Country:    {}".format(entry["country"]))[:max_w] + "\n"
        note += ("Year:       {}".format(entry["year"]))[:max_w] + "\n"
        if entry["subcategory"].lower() != "demo":
            note += ("Category:   {}".format(entry["subcategory"]))[:max_w] + "\n"
        else:
            note += "Category:   Demo\n"
        note += ("Hardware:   {}".format(system))[:max_w] + "\n"
        if entry["issues"]:
            note += ("Issues:     {}".format(entry["issues"]))[:max_w] + "\n"

    if add_note and isinstance(add_note, str):
            note += ("Note:       {}".format(add_note))[:max_w] + "\n"
    elif entry["note"]:
            note += ("Note:       {}".format(entry["note"]))[:max_w] + "\n"

    return note

def ags_fix_filename(name):
    name = name.replace("/", "-").replace("\\", "-").replace(": ", " ").replace(":", " ")
    name = name.replace(" [AGA]", "")
    if name[0] == '(':
        name = name.replace('(', '[', 1).replace(')', ']', 1)
    return name


def ags_create_entry(name, entry, path, note, rank, only_script=False, prefix=None):
    global g_vadjust
    global g_entry_for_path
    max_w = AGS_LIST_WIDTH

    # skip if entry already added at path
    path_id = "{}{}".format(entry["id"] if (entry and entry["id"]) else name, path)
    if path_id in g_entry_for_path:
        return
    else:
        g_entry_for_path.add(path_id)

    # fix path name
    path_prefix = get_ags2_dir()
    if path != path_prefix:
        path_suffix = path.split(path_prefix + "/")[-1]
        path = path_prefix + "/" + "/".join(list(map(ags_fix_filename, path_suffix.split("/"))))

    # base name
    title = rank + ". " if rank else ""
    if prefix:
        title = prefix + " - " + title

    if note and note == "not_available":
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
    if util.is_file(util.path(path, title) + ".run"):
        if entry["category"] == "Demo":
            title += " (" + entry["publisher"] + ")"
        else:
            title += " (" + entry["hardware"].replace("/ECS", "").replace("AGA/CD32", "CD32").replace("OCS/CDTV", "CDTV").replace("/", "-") + ")"
        if only_script:
            title = title.replace(" ", "_")
    if len(title) > max_w:
        title = title[:max_w - 2].strip() + ".."
        if util.is_file(util.path(path, title) + ".run"):
            suffix = 1
            while suffix <= 10:
                title = title[:-1] + str(suffix)
                suffix += 1
                if not util.is_file(util.path(path, title) + ".run"):
                    break

    base_path = util.path(path, title)
    util.make_dir(path)

    # create runfile
    runfile = None
    if get_amiga_whd_dir(entry) is not None or entry_is_notwhdl(entry):
        # videomode
        whd_vmode = "NTSC" if entry["ntsc"] > 0 else "PAL"
        if g_args.ntsc: whd_vmode = "NTSC"
        # vadjust
        vadjust_pal5x = entry["pal_5x"] == 1
        vadjust_name = "pal5" if vadjust_pal5x else "def"
        vadjust_vofs = util.parse_int(entry["v_offset"])
        if not vadjust_vofs:
            vadjust_vofs = 0
        vadjust_name += "_{}".format(vadjust_vofs)
        g_vadjust[vadjust_name] = (vadjust_pal5x, vadjust_vofs)

        if entry_is_notwhdl(entry):
            runfile_path = get_archive_path(entry).replace(".lha", ".run")
            if util.is_file(runfile_path):
                runfile = "set{}\n".format(whd_vmode.lower())
                runfile += "setvadjust {} {}\n".format(vadjust_vofs, "PAL5" if vadjust_pal5x else "")
                with open(runfile_path, 'r') as f: runfile += f.read()
                runfile += "setntsc\n"
                runfile += "setvadjust\n"
        else:
            whd_entrypath = get_amiga_whd_dir(entry)
            if whd_entrypath:
                whd_slave = get_whd_slavename(entry)
                # extra arguments
                whd_cargs = "BUTTONWAIT"
                if entry["slave_args"]:
                    whd_cargs += " " + entry["slave_args"]
                runfile = "cd \"{}\"\n".format(whd_entrypath)
                runfile += "IF NOT EXISTS ENV:whdlspdly\n"
                runfile += "  echo 200 >ENV:whdlspdly\n"
                runfile += "ENDIF\n"
                runfile += "IF NOT EXISTS ENV:whdlqtkey\n"
                runfile += "  echo \"\" >ENV:whdlqtkey\n"
                runfile += "ENDIF\n"
                runfile += "IF EXISTS ENV:whdlvmode\n"
                runfile += "  whdload >NIL: \"{}\" PRELOAD $whdlvmode {} SplashDelay=$whdlspdly $whdlqtkey\n".format(whd_slave, whd_cargs)
                runfile += "ELSE\n"
                runfile += "  setvadjust {} {}\n".format(vadjust_vofs, "PAL5" if vadjust_pal5x else "")
                runfile += "  whdload >NIL: \"{}\" PRELOAD {} {} SplashDelay=$whdlspdly $whdlqtkey\n".format(whd_slave, whd_vmode, whd_cargs)
                runfile += "  setvadjust\n"
                runfile += "ENDIF\n"
    else:
        runfile = "echo \"Title not available.\"" + "\n" + "wait 2"

    if runfile:
        if util.is_file(base_path + ".run"):
            print(" > AGS2 clash:", entry["id"], "-", base_path + ".run")
        else:
            open(base_path + ".run", mode="w", encoding="latin-1").write(runfile)

    if only_script:
        return

    # note
    if note and note == "not_available":
        note = "Title:      " + name.replace("-", " ") + "\n\n"
        note += "WHDLoader not available"
        open(base_path + ".txt", mode="w", encoding="latin-1").write(note)
    elif entry:
        open(base_path + ".txt", mode="w", encoding="latin-1").write(ags_make_note(entry, note))

    # image
    if not g_args.no_img and entry and "id" in entry and util.is_file(util.path("data", "img", entry["id"] + ".iff")):
        shutil.copyfile(util.path("data", "img", entry["id"] + ".iff"), base_path + ".iff")
    return


def ags_create_entries(entries, path, note=None, ranked_list=False):
    global g_entries

    # make dir
    base_dir = get_ags2_dir()
    if path:
        for d in path:
            base_dir = util.path(base_dir, d[:26].strip() + ".ags")
    util.make_dir(base_dir)

    # make note
    if note:
        note = "\n".join([textwrap.fill(p, AGS_INFO_WIDTH) for p in note.replace("\\n", "\n").splitlines()])
        open(base_dir[:-4] + ".txt", mode="w", encoding="latin-1").write(note)

    # collect titles
    pos = 0
    for name in entries:
        pos += 1
        n = name
        title_note = None
        if isinstance(name, tuple) and len(name) == 2:
            n = name[0]
            title_note = name[1]

        # use preferred (fuzzy) entry
        e, pe = get_entry(n)
        if not "--" in name and pe:
            e = pe
        if not e and not pe:
            print(" > WARNING: invalid entry: {}".format(n))
        else:
            g_entries[e["id"]] = e
        rank = None
        if ranked_list:
            rank = str(pos).zfill(len(str(len(entries))))
        ags_create_entry(n, e, base_dir, title_note, rank)

    return

def ags_create_autoentries():
    path = get_ags2_dir()
    d_path = get_ags2_dir()
    if util.is_dir(util.path(path, "[ Demo Scene ].ags")):
        d_path = util.path(path, "[ Demo Scene ].ags")
    for entry in sorted(g_entries.values(), key=operator.itemgetter("title")):
        letter = entry["title_short"][0].upper()
        if letter.isnumeric():
            letter = "0-9"
        year = entry["year"]
        if "x" in year.lower():
            year = "Unknown"

        # Games
        if entry["category"].lower() == "game":
            ags_create_entry(None, entry, util.path(path, "[ All Games ].ags", letter + ".ags"), None, None)
            ags_create_entry(None, entry, util.path(path, "[ All Games, by year ].ags", year + ".ags"), None, None)

        # Demos / Disk Mags
        def add_demo(entry, sort_group, sort_country):
            if sort_group.startswith("The "):
                sort_group = sort_group[4:]
            sort_group = sort_group[:AGS_LIST_WIDTH]
            group_letter = sort_group[0].upper()
            if group_letter.isnumeric():
                group_letter = "0-9"
            if entry["subcategory"].lower().startswith("disk mag"):
                ags_create_entry(None, entry, util.path(d_path, "[ Disk Magazines ].ags"), None, None)
            else:
                if entry["subcategory"].lower().startswith("crack"):
                    ags_create_entry(None, entry, util.path(d_path, "[ Demos, crack intros ].ags"), None, None, prefix=sort_group)
                if entry["subcategory"].lower().startswith("intro"):
                    ags_create_entry(None, entry, util.path(d_path, "[ Demos, 1-64KB ].ags"), None, None)
                group_entry = dict(entry)
                group_entry["title_short"] = group_entry["title"]
                ags_create_entry(None, entry, util.path(d_path, "[ Demos by title ].ags", letter + ".ags"), None, None)
                ags_create_entry(None, group_entry, util.path(d_path, "[ Demos by group ].ags", group_letter + ".ags"), None, None, prefix=sort_group)
                ags_create_entry(None, entry, util.path(d_path, "[ Demos by year ].ags", year + ".ags"), None, None)
                if sort_country:
                    ags_create_entry(None, entry, util.path(d_path, "[ Demos by country ].ags", sort_country + ".ags"), None, None)

        if g_args.all_demos and entry["category"].lower() == "demo":
            groups = entry["publisher"]
            if not groups:
                continue
            for sort_group in groups.split(", "):
                countries = entry["country"]
                if not countries:
                    add_demo(entry, sort_group, None)
                else:
                    for sort_country in countries.split(", "):
                        add_demo(entry, sort_group, sort_country)

        # Run-scripts for randomizer
        if entry["category"].lower() == "game" and not entry["issues"]:
            ags_create_entry(None, entry, util.path(path, "Run"), None, None, only_script=True)

    # Notes for created directories
    if util.is_dir(util.path(path, "[ All Games ].ags")):
        open(util.path(path, "[ All Games ].txt"), mode="w", encoding="latin-1").write("Browse all games alphabetically.")
    if util.is_dir(util.path(path, "[ All Games, by year ].ags")):
        open(util.path(path, "[ All Games, by year ].txt"), mode="w", encoding="latin-1").write("Browse all games by release year.")
    if util.is_dir(util.path(d_path, "[ Demos by group ].ags")):
        open(util.path(d_path, "[ Demos by group ].txt"), mode="w", encoding="latin-1").write("Browse demos by release group.")
    if util.is_dir(util.path(d_path, "[ Demos by country ].ags")):
        open(util.path(d_path, "[ Demos by country ].txt"), mode="w", encoding="latin-1").write("Browse demos by country of origin.")
    if util.is_dir(util.path(d_path, "[ Demos by title ].ags")):
        open(util.path(d_path, "[ Demos by title ].txt"), mode="w", encoding="latin-1").write("Browse demos by title.")
    if util.is_dir(util.path(d_path, "[ Demos by year ].ags")):
        open(util.path(d_path, "[ Demos by year ].txt"), mode="w", encoding="latin-1").write("Browse demos by release year.")
    if util.is_dir(util.path(d_path, "[ Demos, 1-64KB ].ags")):
        open(util.path(d_path, "[ Demos, 1-64KB ].txt"), mode="w", encoding="latin-1").write("Browse demos in the 1/4/40/64KB categories.")
    if util.is_dir(util.path(d_path, "[ Demos, crack intros ].ags")):
        open(util.path(d_path, "[ Demos, crack intros ].txt"), mode="w", encoding="latin-1").write("A glimpse into the origins of the demo scene.")
    if util.is_dir(util.path(d_path, "[ Disk Magazines ].ags")):
        open(util.path(d_path, "[ Disk Magazines ].txt"), mode="w", encoding="latin-1").write("A selection of scene disk magazines.")
    if util.is_dir(util.path(path, "[ Issues ].ags")):
        open(util.path(path, "[ Issues ].txt"), mode="w", encoding="latin-1").write(
            "Titles with known issues on Minimig-AGA.\n(Please report any new or resolved issues!)")

def ags_create_tree(node, path=[]):
    if isinstance(node, list):
        entries = []
        note = None
        ranked_list = False

        for item in node:
            # titles
            if isinstance(item, str):
                entries += [item]
            if isinstance(item, list):
                if len(item) == 2:
                    entries += [(item[0], item[1])]
            # metadata or sub-list
            if isinstance(item, dict):
                if "note" in item:
                    note = str(item["note"])
                    del item["note"]
                if "ranked_list" in item:
                    ranked_list = item["ranked_list"]
                    del item["ranked_list"]
                # item is a sublist (or not_available title)
                for key, value in item.items():
                    if value == "not_available":
                        entries += [(key, value)]
                    else:
                        ags_create_tree(value, path + [key])
        ags_create_entries(entries, path, note, ranked_list)

def ags_add_all(category):
    for r in g_db.cursor().execute('SELECT * FROM titles WHERE category=? AND (redundant IS NULL OR redundant="")', (category,)):
        entry, preferred_entry = get_entry(r["id"])
        if entry:
            if g_args.all_versions:
                g_entries[entry["id"]] = entry
            elif g_args.ecs is False:
                if preferred_entry:
                    g_entries[preferred_entry["id"]] = preferred_entry
                else:
                    g_entries[entry["id"]] = entry
            else:
                if entry_is_aga(entry):
                    continue
                if preferred_entry and entry_is_aga(preferred_entry):
                    g_entries[entry["id"]] = entry
                elif preferred_entry:
                    g_entries[preferred_entry["id"]] = preferred_entry
                else:
                    g_entries[entry["id"]] = entry

# -----------------------------------------------------------------------------
# File system output

def build_pfs(config_base_name, verbose):
    if verbose:
        print("building PFS container...")

    pfs3_bin = util.path("data", "pfs3", "pfs3.bin")
    if not util.is_file(pfs3_bin):
        raise IOError("PFS3 filesystem doesn't exist: " + pfs3_bin)

    if verbose:
        print(" > calculating partition sizes...")

    block_size = 512
    heads = 4
    sectors = 63
    cylinder_size = block_size * heads * sectors
    fs_overhead = 1.0718
    num_cyls_rdb = 1
    total_cyls = num_cyls_rdb

    partitions = [] # (partition name, cylinders)
    for f in sorted(os.listdir(g_clone_dir)):
        if util.is_dir(util.path(g_clone_dir, f)) and is_amiga_devicename(f):
            mb_free = 100 if f == "DH0" else 50
            cyls = int(fs_overhead * (util.get_dir_size(util.path(g_clone_dir, f), block_size)[2] + (mb_free * 1024 * 1024))) // cylinder_size
            partitions.append(("DH" + str(len(partitions)), cyls))
            total_cyls += cyls

    out_hdf = util.path(g_out_dir, config_base_name + ".hdf")
    if util.is_file(out_hdf):
        os.remove(out_hdf)

    if verbose: print(" > creating pfs container ({}MB)...".format((total_cyls * cylinder_size) // (1024 * 1024)))
    r = subprocess.run(["rdbtool", out_hdf,
                        "create", "chs={},{},{}".format(total_cyls + 1, heads, sectors), "+", "init", "rdb_cyls={}".format(num_cyls_rdb)])

    if verbose: print(" > adding filesystem...")
    r = subprocess.run(["rdbtool", out_hdf, "fsadd", pfs3_bin, "fs=PFS3"], stdout=subprocess.PIPE)

    if verbose:
        print(" > adding partitions...")

    # add boot partition
    part = partitions.pop(0)
    if verbose: print("    > " + part[0])
    r = subprocess.run(["rdbtool", out_hdf,
                        "add", "name={}".format(part[0]),
                        "start={}".format(num_cyls_rdb), "size={}".format(part[1]),
                        "fs=PFS3", "block_size={}".format(block_size), "max_transfer=0x0001FE00", "mask=0x7FFFFFFE",
                        "num_buffer=300", "bootable=True"], stdout=subprocess.PIPE)

    # add subsequent partitions
    for part in partitions:
        if verbose: print("    > " + part[0])
        r = subprocess.run(["rdbtool", out_hdf, "free"], stdout=subprocess.PIPE, universal_newlines=True)
        free = make_tuple(r.stdout.splitlines()[0])
        free_start = int(free[0])
        free_end = int(free[1])
        part_start = free_start
        part_end = part_start + part[1]
        if part_end > free_end:
            part_end = free_end
        r = subprocess.run(["rdbtool", out_hdf,
                            "add", "name={}".format(part[0]),
                            "start={}".format(part_start), "end={}".format(part_end),
                            "fs=PFS3", "block_size={}".format(block_size), "max_transfer=0x0001FE00",
                            "mask=0x7FFFFFFE", "num_buffer=300"], stdout=subprocess.PIPE)
    return

# -----------------------------------------------------------------------------
# Copy base image, extra files

def extract_base_image(base_hdf, dest):
    _ = subprocess.run(["xdftool", base_hdf, "read", "/", dest])

# -----------------------------------------------------------------------------

def main():
    global g_args, g_db, g_out_dir, g_clone_dir

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", dest="config_file", required=True, metavar="FILE", type=lambda x: util.argparse_is_file(parser, x),  help="configuration file")
    parser.add_argument("-o", "--out_dir", dest="out_dir", metavar="FILE", type=lambda x: util.argparse_is_dir(parser, x),  help="output directory")
    parser.add_argument("-b", "--base_hdf", dest="base_hdf", metavar="FILE", help="base HDF image")
    parser.add_argument("-a", "--ags_dir", dest="ags_dir", metavar="FILE", type=lambda x: util.argparse_is_dir(parser, x),  help="AGS2 configuration directory")
    parser.add_argument("-d", "--add_dir", dest="add_dirs", action="append", help="add dir to amiga filesystem (example 'DH1:Music::~/Amiga/Music')")

    parser.add_argument("--all_games", dest="all_games", action="store_true", default=False, help="include all games in database")
    parser.add_argument("--all_demos", dest="all_demos", action="store_true", default=False, help="include all demos in database")
    parser.add_argument("--all_versions", dest="all_versions", action="store_true", default=False, help="include all non-redundant versions of titles (if --all_games)")
    parser.add_argument("--no_autolists", dest="no_autolists", action="store_true", default=False, help="don't add any auto-lists")

    parser.add_argument("--no_img", dest="no_img", action="store_true", default=False, help="don't copy screenshots")
    parser.add_argument("--ecs_versions", dest="ecs", action="store_true", default=False, help="prefer OCS/ECS versions (if --all_games)")
    parser.add_argument("--force_ntsc", dest="ntsc", action="store_true", default=False, help="force NTSC video mode")

    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", default=False, help="verbose output")

    try:
        g_args = parser.parse_args()
        g_db = util.get_db(g_args.verbose)

        if g_args.out_dir:
            g_out_dir = g_args.out_dir

        g_clone_dir = util.path(g_out_dir, "tmp")
        if util.is_dir(g_clone_dir):
            shutil.rmtree(g_clone_dir)
        util.make_dir(util.path(g_clone_dir, "DH0"))

        config_base_name = os.path.splitext(os.path.basename(g_args.config_file))[0]

        data_dir = "data"
        if not util.is_dir(data_dir):
            raise IOError("data dir doesn't exist: " + data_dir)

        # extract base image
        base_hdf = g_args.base_hdf
        if not base_hdf:
            base_hdf = util.path(paths.content(), "base", "base.hdf")
        if not util.is_file(base_hdf):
            raise IOError("base HDF doesn't exist: " + base_hdf)
        if g_args.verbose:
            print("extracting base HDF image... ({})".format(base_hdf))
        extract_base_image(base_hdf, get_boot_dir())

        # parse menu
        menu = None
        if g_args.verbose:
            print("parsing menu...")
        menu = util.yaml_load(g_args.config_file)
        if not isinstance(menu, list):
            raise ValueError("config file not a list: " + g_args.config_file)

        # copy base AGS2 config, create database
        if g_args.verbose:
            print("building AGS2 database...")

        base_ags2 = g_args.ags_dir
        if not base_ags2:
            base_ags2 = util.path("data", "ags2")
        if not util.is_dir(base_ags2):
            raise IOError("AGS2 configuration directory doesn't exist: " + base_ags2)
        if g_args.verbose:
            print(" > using configuration: " + base_ags2)

        util.copytree(base_ags2, get_ags2_dir())

        if menu:
            ags_create_tree(menu)
        if g_args.all_games:
            ags_add_all("Game")
        if g_args.all_demos:
            ags_add_all("Demo")
            ags_add_all("Mags")

        if not g_args.no_autolists:
            ags_create_autoentries()

        if VADJUST_CREATE_RANGE:
            create_vadjust_dats(None)
        else:
            create_vadjust_dats(g_vadjust)

        # extract whdloaders
        if g_args.verbose: print("extracting {} content archives...".format(len(g_entries.items())))
        extract_entries(g_entries)

        # copy extra files
        config_extra_dir = util.path(os.path.dirname(g_args.config_file), config_base_name)
        if util.is_dir(config_extra_dir):
            if g_args.verbose: print("copying configuration extras...")
            util.copytree(config_extra_dir, g_clone_dir)

        # copy additional directories
        if g_args.add_dirs:
            if g_args.verbose: print("copying additional directories...")
            for s in g_args.add_dirs:
                d = s.split("::")
                if util.is_dir(d[0]):
                    dest = util.path(g_clone_dir, d[1].replace(":", "/"))
                    print(" > copying '" + d[0] +"' to '" + d[1] + "'")
                    util.copytree(d[0], dest)
                else:
                    print(" > WARNING: '" + d[1] + "' doesn't exist")

        # build PFS container
        build_pfs(config_base_name, g_args.verbose)

        # set up cloner environment
        cloner_adf = util.path("data", "cloner", "boot.adf")
        cloner_cfg = util.path("data", "cloner", "template.fs-uae")
        clone_script = util.path(os.path.dirname(g_args.config_file), config_base_name) + ".clonescript"
        if util.is_file(cloner_adf) and util.is_file(cloner_cfg) and util.is_file(clone_script):
            if g_args.verbose: print("copying cloner config...")
            shutil.copyfile(cloner_adf, util.path(g_clone_dir, "boot.adf"))
            # create config from template
            with open(cloner_cfg, 'r') as f:
                cfg = f.read()
                cfg = cfg.replace("<config_base_name>", config_base_name)
                cfg = cfg.replace("$AGSTEMP", paths.tmp())
                cfg = cfg.replace("$AGSDEST", util.path(os.getenv("AGSDEST")))
                cfg = cfg.replace("$FSUAEROM", util.path(os.getenv("FSUAEROM")))
                open(util.path(g_clone_dir, "cfg.fs-uae"), mode="w").write(cfg)
            # copy clone script and write fs-uae metadata
            shutil.copyfile(clone_script, util.path(g_clone_dir, "clone"))
            open(util.path(g_clone_dir, "clone.uaem"), mode="w").write("-s--rwed 2020-02-02 22:22:22.00")
        else:
            print("WARNING: cloner config files not found")

        # clean output directory
        for r, _, f in os.walk(g_clone_dir):
            for name in f:
                path = util.path(r, name)
                if name == ".DS_Store":
                    os.remove(path)
        return 0

    # except Exception as err:
    except IOError as err:
        print("error - {}".format(err))
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
