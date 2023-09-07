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
# ntsc: Video mode and pixel aspect ratio
#   0 = PAL title that will be run at 50Hz (PAL, 16:15 PAR @ 4X, 1:1 PAR @ 5X)
#   1 = PAL title that will be run at 60Hz (PAL60, 16:15 PAR @ 4X, 1:1 PAR @ 5X)
#   2 = "World" title that will be run at 60Hz (NTSC, 16:15 PAR @ 4X, 1:1 PAR @ 5X)
#   3 = NTSC title that will be run at 60Hz (NTSC, 16:15 PAR @ 4X, 1:1 PAR @ 5X)
#   4 = NTSC title that will be run at 60Hz and was likely designed for narrow PAR ("Sachs NTSC", 5:6 PAR @ 5X)
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
from ags_fs import build_pfs, extract_base_image, convert_filename_uae2a
from ags_make import make_autoentries, make_runscripts, make_tree
from ags_query import entry_is_notwhdl, get_archive_path, get_entry, get_whd_dir
from ags_types import EntryCollection

# -----------------------------------------------------------------------------

def add_all(db: Connection, c: EntryCollection, category: str, exclude_subcategories=None) -> None:
    for r in db.cursor().execute('SELECT * FROM titles WHERE category=? AND (redundant IS NULL OR redundant="")', (category,)):
        entry, preferred_entry = get_entry(db, r["id"])
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

def extract_entries(clone_path, entries):
    unarchived = set()
    for entry in entries:
        if "archive_path" in entry and not entry["archive_path"] in unarchived:
            extract_entry(clone_path, entry)
            unarchived.add(entry["archive_path"])

def extract_entry(clone_path, entry):
    arc_path = get_archive_path(entry)
    if not arc_path:
        print(" > WARNING: archive not found for", entry["id"])
    else:
        dest = get_whd_dir(clone_path, entry)
        if entry_is_notwhdl(entry):
            util.lha_extract(arc_path, dest)
        else:
            util.lha_extract(arc_path, dest)
            info_path = util.path(dest, entry["slave_dir"] + ".info")
            if util.is_file(info_path):
                os.remove(info_path)

# -----------------------------------------------------------------------------
# command line interface

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", dest="config_file", required=True, metavar="FILE", type=lambda x: util.argparse_is_file(parser, x),  help="configuration file")
    parser.add_argument("-o", "--out-dir", dest="out_dir", metavar="FILE", type=lambda x: util.argparse_is_dir(parser, x),  help="output directory")
    parser.add_argument("-b", "--base-hdf", dest="base_hdf", metavar="FILE", help="base HDF image")
    parser.add_argument("-a", "--ags-dir", dest="ags_dir", metavar="FILE", type=lambda x: util.argparse_is_dir(parser, x),  help="AGS2 configuration directory")
    parser.add_argument("-d", "--add-dir", dest="add_dirs", action="append", help="add dir to amiga filesystem (example '~/Amiga/Music::DH1:Music')")

    parser.add_argument("--all-games", dest="all_games", action="store_true", default=False, help="include all games")
    parser.add_argument("--all-demos", dest="all_demos", action="store_true", default=False, help="include all demos")
    parser.add_argument("--all-demoscene", dest="all_demoscene", action="store_true", default=False, help="include all demo scene content")
    parser.add_argument("--auto-lists", dest="auto_lists", action="store_true", default=False, help="create automatic lists")
    parser.add_argument("--only-ags-tree", dest="only_ags_tree", action="store_true", default=False, help="only generate AGS tree")

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

        data_dir = "data"
        if not util.is_dir(data_dir):
            raise IOError("data dir not found ({})".format(data_dir))

        # parse configuration
        config_dir = os.path.dirname(args.config_file)
        config_base_name = os.path.splitext(os.path.basename(args.config_file))[0]

        runscript_template_path = util.path(config_dir, config_base_name) + ".runscript"
        if not util.is_file(runscript_template_path):
            raise IOError("run script template not found ({})".format(runscript_template_path))

        if args.verbose: print("parsing menu...")
        menu = util.yaml_load(args.config_file)
        if not isinstance(menu, list):
            raise ValueError("config file not a list ({})".format(args.config_file))
        with open(runscript_template_path, 'r') as f:
            runscript_template = f.read()

        # extract base image
        base_hdf: str | None = args.base_hdf
        if not base_hdf:
            base_hdf = util.path(paths.content(), "base", "base.hdf")
        if not util.is_file(base_hdf):
            raise IOError("base HDF not found ({})".format(base_hdf))
        if not args.only_ags_tree:
            if args.verbose: print("extracting base HDF image: {}".format(base_hdf))
            extract_base_image(base_hdf, amiga_boot_path)

        # copy base AGS2 config
        if args.verbose: print("building AGS2 tree...")
        base_ags2 = args.ags_dir
        if not base_ags2:
            base_ags2 = util.path("data", "ags2")
        if not util.is_dir(base_ags2):
            raise IOError("configuration directory not found ({})".format(base_ags2))
        if args.verbose:
            print(" > using configuration: {}".format(base_ags2))
        util.copytree(base_ags2, amiga_ags_path)

        # collect entries
        if menu:
            make_tree(db, collection, amiga_ags_path, menu, template=runscript_template)
        if args.all_games:
            add_all(db, collection, "Game")
        if args.all_demos:
            add_all(db, collection, "Demo", exclude_subcategories=["Disk Magazine", "Slide Show"])
        if args.all_demoscene:
            add_all(db, collection, "Demo")
        if args.all_games or args.all_demos or args.all_demoscene or args.auto_lists:
            make_autoentries(collection, amiga_ags_path, games=args.all_games|args.auto_lists, demos=args.all_demos|args.all_demoscene|args.auto_lists)

        # generate run scripts
        make_runscripts(collection, amiga_ags_path, template=runscript_template)

        # extract whdloaders
        if not args.only_ags_tree:
            if args.verbose: print("extracting {} content archives...".format(len(collection.by_id.items())))
            extract_entries(clone_path, collection.ids())

        # copy layers
        if args.verbose: print("adding layers...")
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
                    if args.verbose: print(" > '{}' -> '{}'".format(src, dst))
                    util.copytree(src_dir, util.path(clone_path, dst[1:]))

        # copy additional directories
        if not args.only_ags_tree and args.add_dirs:
            if args.verbose: print("copying additional directories...")
            for s in args.add_dirs:
                d = s.split("::")
                if len(d) != 2:
                    raise ValueError("--add-dir parameter malformed ({})".format(s))
                elif util.is_dir(d[0]):
                    dest = util.path(clone_path, d[1].replace(":", "/"))
                    if args.verbose: print(" > '{}' -> '{}'".format(d[0], d[1]))
                    util.copytree(d[0], dest)
                else:
                    raise IOError("--add-dir source not found ({})".format(d[0]))

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

            if cache:
                cachefile = "{}\n".format(len(cache))
                for line in cache: cachefile += "{}\n".format(convert_filename_uae2a(line))
                open(util.path(path, ".dir"), mode="w", encoding="latin-1").write(cachefile)

        # build PFS container
        if not args.only_ags_tree:
            build_pfs(util.path(out_dir, config_base_name + ".hdf"), clone_path, args.verbose)

        # set up cloner environment
        if not args.only_ags_tree:
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
                raise IOError("cloner config files not found ({}, {}, {})".format(cloner_adf, cloner_cfg, clone_script))

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
            content_path = util.path(amiga_ags_path, "RunQuiet", list_def[0])
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
        print("io error - {}".format(err))
        sys.exit(1)
    except ValueError as err:
        print("value error - {}".format(err))
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
