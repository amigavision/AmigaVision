#!/usr/bin/env python3

# AGSImager: Indexer

import argparse
import hashlib
import os
import sys

from lhafile import LhaFile, is_lhafile
from ruamel import yaml

import ags_paths as paths
import ags_util as util

# -----------------------------------------------------------------------------
# Make dictionary of whdload archives

def index_whdload_archives(basedir):
    basedir += os.sep
    print("enumerating archives..", end="", flush=True)
    count = 0
    d = {}
    for r, _, f in os.walk(basedir):
        for file in f:
            if file.endswith(".lha"):
                count += 1
                if count % 100 == 0:
                    print(".", end="", flush=True)
                path = util.path(r, file)
                if not is_lhafile(path):
                    print("\n{} is not a valid lha file".format(path), flush=True)
                    continue
                db_path = path.split(basedir)[1]
                slave_category = db_path.split(os.sep)[0]

                if slave_category in ["game", "demo", "mags"]:
                    arc = LhaFile(path)
                    for n in arc.namelist():
                        n = n.replace("\\", "/")
                        if n.lower().endswith(".slave"):
                            if len(n.split("/")) > 2:
                                pass  # skip slaves beneath root
                            else:
                                slave_id = slave_category + "--" + n[:-6].replace("/", "--").lower()
                                slave_ver = "v1.0"
                                try:
                                    verstr = file[:-4].split("_")[1]
                                    if verstr.startswith("v"):
                                        slave_ver = verstr
                                except Exception:
                                    pass
                                d[slave_id] = {"id": slave_id, "archive_path": db_path, "slave_path": n, "slave_version": slave_ver}

                elif slave_category in ["game-notwhdl", "demo-notwhdl", "mags-notwhdl"]:
                    slave_id = slave_category + "--" + os.path.splitext(os.path.basename(path))[0].lower()
                    if util.is_file(path.replace(".lha", ".run")):
                        d[slave_id] = {"id": slave_id, "archive_path": db_path, "slave_path": None, "slave_version": None}

    print("\n", flush=True)
    return d

# -----------------------------------------------------------------------------
# Make and verify manifests for lha files in content directory

def make_manifests(basedir, only_missing=False):
    basedir += os.sep
    print("making manifests..", end="", flush=True)
    count = 0
    for r, _, f in os.walk(basedir):
        for file in f:
            if make_manifest(util.path(r, file), only_missing):
                count += 1
                if count % 100 == 0: print(".", end="", flush=True)
    print("\n", flush=True)
    return

def make_manifest(path, only_missing=False):
    yaml_path = path + ".yaml"
    contents = None
    if only_missing and util.is_file(yaml_path):
        return None
    if path.endswith(".lha") and is_lhafile(path):
        contents = make_lha_manifest(path)
    if contents:
        with open(yaml_path, 'w') as f:
            yaml.round_trip_dump(contents, f, explicit_start=True, version=(1, 2))
    return contents

def make_lha_manifest(path):
    contents = dict()
    arc = LhaFile(path)
    for n in arc.namelist():
        hasher = hashlib.sha256()
        hasher.update(arc.read(n))
        contents[n] = "{}".format(hasher.hexdigest())
    return contents

def verify_manifests(basedir):
    basedir += os.sep
    print("verifying manifests...")
    errors = 0
    for r, _, f in os.walk(basedir):
        for file in f:
            error = None
            path = util.path(r, file)
            if file.endswith(".lha.yaml"):
                error = verify_lha_manifest(path, path[:-5])
            if error:
                print(error)
                errors += 1
    if errors > 0:
        print("manifest verification completed with {} error(s)".format(errors))
    else:
        print("manifest verification completed: all good")
    return

def verify_lha_manifest(manifest_path, lha_path):
    if not util.is_file(lha_path):
        return "lha file missing: {}".format(lha_path)
    elif not is_lhafile(lha_path):
         return "lha file unreadable: {}".format(lha_path)
    else:
        manifest = load_manifest(manifest_path)
        if not isinstance(manifest, dict):
            return "manifest corrupt: {}".format(manifest_path)
        else:
            arc = LhaFile(lha_path)
            arc_names = arc.namelist()
            for mf, md in manifest.items():
                if not mf in arc_names:
                    return "file '{}' missing in archive '{}'".format(mf, lha_path)
                else:
                    hasher = hashlib.sha256()
                    hasher.update(arc.read(mf))
                    if hasher.hexdigest() != md:
                        return "incorrect checksum for file '{}' in '{}'".format(mf, lha_path)
    return None

def load_manifest(p):
    try:
        with open(p, 'r') as f:
            return yaml.safe_load(f)
    except:
        return None

# -----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--make-sqlite", dest="make_sqlite", action="store_true", default=False, help="make sqlite db from cvs (if none exists or if cvs is newer than existing)")
    parser.add_argument("--make-csv", dest="make_csv", action="store_true", default=False, help="make csv from sqlite db")
    parser.add_argument("--make-manifests", dest="make_manifests", action="store_true", default=False, help="make manifest files")
    parser.add_argument("--only-missing", dest="only_missing", action="store_true", default=False, help="create only missing manifests")
    parser.add_argument("--verify-manifests", dest="verify_manifests", action="store_true", default=False, help="verify that contents match manifests")
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", default=False, help="verbose output")

    try:
        paths.verify()
        args = parser.parse_args()

        if args.make_csv:
            util.write_csv()
            return 0

        db = util.get_db(args.verbose)

        if args.make_sqlite:
            db.close()
            return 0

        titles_dir = paths.titles()
        if not util.is_dir(titles_dir):
            raise IOError("titles dir not found ({})".format(titles_dir))

        if args.make_manifests:
            make_manifests(titles_dir, only_missing=args.only_missing)
            return 0

        if args.verify_manifests:
            verify_manifests(titles_dir)
            return 0

        # remove missing archive_paths from db
        for r in db.cursor().execute("SELECT * FROM titles"):
            if r["archive_path"] and not util.is_file(util.path(titles_dir, r["archive_path"])):
                print("archive removed:", r["id"])
                print("  >>", r["archive_path"])
                db.cursor().execute("UPDATE titles SET archive_path=NULL,slave_path=NULL,slave_version=NULL WHERE id=?;", (r["id"],))
                print()

        # enumerate whdl archives, correlate with db
        for _, arc in index_whdload_archives(titles_dir).items():
            rows = db.cursor().execute("SELECT * FROM titles WHERE (id = ?) OR (id LIKE ?);", (arc["id"], arc["id"] + '--%',)).fetchall()
            if not rows:
                print("no db entry:", arc["archive_path"])
                print("  >>", arc["id"])
                print()
                continue
            for row in rows:
                if not row["archive_path"]:
                    db.cursor().execute("UPDATE titles SET archive_path=?,slave_path=?,slave_version=? WHERE id=?;",
                                        (arc["archive_path"], arc["slave_path"], arc["slave_version"], row["id"]))
                    print("archive added: " + arc["archive_path"] + " -> " +row["id"])
                    print()

        # list missing content
        if args.verbose:
            missing_archives = []
            missing_images = []
            missing_manifests = []
            for r in db.cursor().execute("SELECT * FROM titles"):
                if not r["archive_path"]:
                    missing_archives.append(r["id"])
                elif not util.is_file(util.path(titles_dir, r["archive_path"]) + ".yaml"):
                    missing_manifests.append(util.path(titles_dir, r["archive_path"]) + ".yaml")
                if not util.is_file("data/img/" + r["id"] + ".iff"):
                    missing_images.append(r["id"])
            if missing_archives:
                print("titles missing archives:")
                for id in missing_archives:
                    print("  >> {}".format(id))
                print()
            if missing_images:
                print("titles missing images:")
                for id in missing_images:
                    print("  >> {}".format(id))
                print()
            if missing_manifests:
                print("missing manifests (generate with 'make missing-manifests'):")
                for id in missing_manifests:
                    print("  >> {}".format(id))
                print()

        db.commit()
        db.close()
        return 0

    # except Exception as err:
    except IOError as err:
        print("error - {}".format(err))
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
