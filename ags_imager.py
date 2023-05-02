#!/usr/bin/env python3

# AGSImager

# Database fields:
#
# id: Unique title identifier
# title: Full title (displayed in info box)
# title_short: Short title (displayed in list)
# redundant: Exclude in add_all operations
# preferred_version: Use this version instead if title is fuzzy matched (i.e. not using precise name in yaml config)
# hardware: Hardware the title was originally targeting (OCS, OCS/CD, OCS/CDTV, AGA, AGA/CD, AGA/CD32, etc)
# aga: Title is AGA only
# ntsc: Video mode and pixel aspect ratio
#   0 = PAL title that will be run at 50Hz (PAL, 16:15 PAR @ 4X or 5X, 1:1 PAR @ 6X)
#   1 = PAL title that will be run at 60Hz (PAL60, 16:15 PAR @ 5X, 1:1 PAR @ 6X)
#   2 = "World" title that will be run at 60Hz (NTSC, 16:15 PAR @ 5X, 1:1 PAR @ 6X)
#   3 = NTSC title that will be run at 60Hz (NTSC, 16:15 PAR @ 5X, 1:1 PAR @ 6X)
#   4 = NTSC title that will be run at 60Hz and was likely designed for narrow PAR ("Sachs NTSC", 5:6 PAR @ 5X)
# scale: Viewport integer scale factor at 1080p (PAL: 4-6, NTSC: 5-6)
# v_offset: Viewport vertical offset (lower value -> screen is shifted downwards)
#   Expressible range (higher values allowed but have no effect):
#   - NTSC: -16...9
#   - PAL5: -11...59
#   - PAL4: -11...5
# killaga: Use killaga hack when invoking whdload
# gamepad: Title supports more than one button
# lightgun: Title supports light gun
# note: Extra text displayed in info box as "Note:"
# issues: Extra text displayed in info box as "Issues:"
# hack: Extra text displayed in info box as "Hack info:"
# release_date: Release date (YYYY or YYYY-MM-DD)
# country: Country of origin (comma separated list)
# language: Languages supported (comma separated list)
# developer: Developer (comma separated list)
# publisher: Publisher (comma separated list)
# players: Number of players supported (displayed in info box)
# slave_args: Extra arguments passed in whdl invokation
# slave_version: WHDL install version (set by ags_index)
# slave_path: Path to WHDL slave in archive (set by ags_index)
# archive_path: th to WHDL install archive (set by ags_index)
# category: Category/genre (only used for demo scene auto-lists at the moment)
# subcategory: Subcategory/genre (only used for demo scene auto-lists at the moment)
# hol_id: Hall of Light ID
# lemon_id: Lemon Amiga ID

import argparse
import os
import shutil
import subprocess
import sys
from sqlite3 import Connection

import ags_paths as paths
import ags_util as util
from ags_fs import build_pfs, extract_base_image, convert_filename_uae2a, convert_filename_a2uae
from ags_make import make_autoentries, make_tree
from ags_query import entry_is_aga, entry_is_notwhdl, get_archive_path, get_entry, get_whd_dir
from ags_types import EntryCollection
from make_vadjust import VADJUST_MAX, VADJUST_MIN, make_vadjust

# -----------------------------------------------------------------------------

def add_all(db: Connection, entries: EntryCollection, category, all_versions, prefer_ecs):
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

def extract_entries(clone_path, entries):
    unarchived = set()
    for entry in entries:
        if "archive_path" in entry and not entry["archive_path"] in unarchived:
            extract_entry(clone_path, entry)
            unarchived.add(entry["archive_path"])

def extract_entry(clone_path, entry):
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

def make_vadjust_dats(path):
    util.make_dir(path)
    for i in range(VADJUST_MIN, VADJUST_MAX+1):
        open(util.path(path, "xd_{}".format(i)), mode="wb").write(make_vadjust(v_shift=i))
        open(util.path(path, "x5_{}".format(i)), mode="wb").write(make_vadjust(scale=5, v_shift=i))
        open(util.path(path, "x6_{}".format(i)), mode="wb").write(make_vadjust(scale=6, v_shift=i))
        open(util.path(path, "xS_{}".format(i)), mode="wb").write(make_vadjust(scale=5, v_shift=i, sachs=True))

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
        collection = EntryCollection()

        if args.out_dir:
            out_dir = args.out_dir

        clone_path = util.path(out_dir, "tmp")
        amiga_boot_path = util.path(clone_path, "DH0")
        amiga_ags_path = util.path(amiga_boot_path, "AGS2")

        util.rm_path(clone_path)
        util.make_dir(util.path(clone_path, "DH0"))

        config_base_name = os.path.splitext(os.path.basename(args.config_file))[0]

        data_dir = "data"
        if not util.is_dir(data_dir):
            raise IOError("data dir doesn't exist: " + data_dir)

        # parse configuration
        menu = None
        if args.verbose: print("parsing menu...")
        menu = util.yaml_load(args.config_file)
        if not isinstance(menu, list):
            raise ValueError("config file not a list: " + args.config_file)

        runfile_template_path = util.path(os.path.dirname(args.config_file), config_base_name) + ".runfile"
        if not util.is_file(runfile_template_path):
            raise IOError("AGS2 runfile template doesn't exist: " + runfile_template_path)
        with open(runfile_template_path, 'r') as f:
            runfile_template = f.read()

        # extract base image
        base_hdf = args.base_hdf
        if not base_hdf:
            base_hdf = util.path(paths.content(), "base", "base.hdf")
        if not util.is_file(base_hdf):
            raise IOError("base HDF doesn't exist: " + base_hdf)
        if args.verbose: print("extracting base HDF image... ({})".format(base_hdf))
        extract_base_image(base_hdf, amiga_boot_path)

        # copy base AGS2 config
        if args.verbose: print("building AGS2 tree...")
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
            make_tree(db, collection, amiga_ags_path, menu, template=runfile_template)
        if args.all_games:
            add_all(db, collection, "Game", args.all_versions, args.prefer_ecs)
        if args.all_demos:
            add_all(db, collection, "Demo", args.all_versions, args.prefer_ecs)
        if args.all_games or args.all_demos:
            make_autoentries(collection, amiga_ags_path, args.all_games, args.all_demos, template=runfile_template)

        # extract whdloaders
        if args.verbose: print("extracting {} content archives...".format(len(collection.by_id.items())))
        extract_entries(clone_path, collection.ids())

        make_vadjust_dats(util.path(amiga_boot_path, "S", "vadjust_dat"))

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

            if len(cache) > 0:
                cachefile = "{}\n".format(len(cache))
                for line in cache: cachefile += "{}\n".format(convert_filename_uae2a(line))
                open(util.path(path, ".dir"), mode="w", encoding="latin-1").write(cachefile)

        # build PFS container
        build_pfs(util.path(out_dir, config_base_name + ".hdf"), clone_path, args.verbose)

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
        util.rm_path(list_dir)
        util.make_dir(list_dir)
        for list_def in [("Game", "games.txt"), ("Demo", "demos.txt")]:
            content_path = util.path(amiga_ags_path, "Run", list_def[0])
            if util.is_dir(content_path):
                listing = "\n".join(sorted(os.listdir(util.path(amiga_ags_path, "Run", list_def[0])), key=str.casefold))
                open(util.path(list_dir, list_def[1]), mode="w", encoding="latin-1").write(listing)

        # run post-build script
        post_build_sh_path = util.path(os.path.dirname(args.config_file), config_base_name) + ".sh"
        if util.is_file(post_build_sh_path):
            r = subprocess.call(["sh", post_build_sh_path])
            if r != 0: return r

        # done
        return 0

    # except Exception as err:
    except IOError as err:
        print("error - {}".format(err))
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
