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
# Manifest paths

def manifest_path_for_archive(titles_dir, manifests_dir, archive_path):
    rel_path = os.path.relpath(archive_path, titles_dir)
    return util.path(manifests_dir, rel_path + ".yaml")

def archive_path_for_manifest(titles_dir, manifests_dir, manifest_path):
    rel_path = os.path.relpath(manifest_path, manifests_dir)
    if not rel_path.endswith(".lha.yaml"):
        return None
    return util.path(titles_dir, rel_path[:-5])

def find_stale_manifests(titles_dir, manifests_dir):
    stale_manifests = []
    for r, _, f in os.walk(manifests_dir):
        for file in f:
            if not file.endswith(".lha.yaml"):
                continue
            manifest_path = util.path(r, file)
            archive_path = archive_path_for_manifest(titles_dir, manifests_dir, manifest_path)
            if archive_path and not util.is_file(archive_path):
                stale_manifests.append(manifest_path)
    return sorted(stale_manifests)

def prune_manifests(titles_dir, manifests_dir, apply=False):
    stale_manifests = find_stale_manifests(titles_dir, manifests_dir)
    if stale_manifests:
        heading = "• Stale manifests pruned:" if apply else "• Stale manifests found (rerun with --apply to prune):"
        print(heading)
        for manifest_path in stale_manifests:
            print(manifest_path)
            if apply:
                os.remove(manifest_path)
        print()
    else:
        print("No stale manifests found")
    return stale_manifests

def sync_manifests(titles_dir, manifests_dir, apply=False):
    make_manifests(titles_dir, manifests_dir, only_missing=True)
    stale_manifests = prune_manifests(titles_dir, manifests_dir, apply=apply)
    if stale_manifests and not apply:
        print("Manifest sync completed with {} stale manifest(s) pending prune".format(len(stale_manifests)))
    else:
        print("Manifest sync completed")
    return stale_manifests

# -----------------------------------------------------------------------------
# Make dictionary of whdload archives

def index_whdload_archives(basedir):
    basedir += os.sep
    print("Enumerating archives...", end="", flush=True)
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

def make_manifests(titles_dir, manifests_dir, only_missing=False):
    titles_dir += os.sep
    print("Making manifests...", end="", flush=True)
    count = 0
    for r, _, f in os.walk(titles_dir):
        for file in f:
            if make_manifest(titles_dir, manifests_dir, util.path(r, file), only_missing):
                count += 1
                if count % 100 == 0: print(".", end="", flush=True)
    print("\n", flush=True)
    return

def make_manifest(titles_dir, manifests_dir, path, only_missing=False):
    yaml_path = manifest_path_for_archive(titles_dir, manifests_dir, path)
    contents = None
    if only_missing and util.is_file(yaml_path):
        return None
    if path.endswith(".lha") and is_lhafile(path):
        contents = make_lha_manifest(path)
    if contents:
        os.makedirs(os.path.dirname(yaml_path), exist_ok=True)
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

def verify_manifests(titles_dir, manifests_dir):
    manifests_dir += os.sep
    print("Verifying manifests...")
    errors = 0
    for r, _, f in os.walk(manifests_dir):
        for file in f:
            error = None
            path = util.path(r, file)
            if file.endswith(".lha.yaml"):
                lha_path = archive_path_for_manifest(titles_dir, manifests_dir, path)
                error = verify_lha_manifest(path, lha_path)
            if error:
                print(error)
                errors += 1
    if errors > 0:
        print("Manifest verification completed with {} error(s)".format(errors))
    else:
        print("Manifest verification completed: all good")
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
                    return "• File '{}' missing in archive '{}'".format(mf, lha_path)
                else:
                    hasher = hashlib.sha256()
                    hasher.update(arc.read(mf))
                    if hasher.hexdigest() != md:
                        return "• Incorrect checksum for file '{}' in '{}'".format(mf, lha_path)
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
    parser.add_argument("--sync-manifests", dest="sync_manifests", action="store_true", default=False, help="create missing manifests and report/prune stale manifests")
    parser.add_argument("--prune-manifests", dest="prune_manifests", action="store_true", default=False, help="report or prune manifests without a matching archive")
    parser.add_argument("--apply", dest="apply", action="store_true", default=False, help="apply changes for destructive manifest operations")
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
            raise IOError("Titles dir not found ({})".format(titles_dir))
        manifests_dir = paths.manifests()

        if args.make_manifests:
            make_manifests(titles_dir, manifests_dir, only_missing=args.only_missing)
            return 0

        if args.verify_manifests:
            verify_manifests(titles_dir, manifests_dir)
            return 0

        if args.sync_manifests:
            stale_manifests = sync_manifests(titles_dir, manifests_dir, apply=args.apply)
            return 1 if stale_manifests and not args.apply else 0

        if args.prune_manifests:
            stale_manifests = prune_manifests(titles_dir, manifests_dir, apply=args.apply)
            return 1 if stale_manifests and not args.apply else 0

        # remove missing archive_paths from db
        for r in db.cursor().execute("SELECT * FROM titles"):
            if r["archive_path"] and not util.is_file(util.path(titles_dir, r["archive_path"])):
                print("• Archive removed:", r["id"])
                print(r["archive_path"])
                db.cursor().execute("UPDATE titles SET archive_path=NULL,slave_path=NULL,slave_version=NULL WHERE id=?;", (r["id"],))
                print()

        # enumerate whdl archives, correlate with db
        for _, arc in index_whdload_archives(titles_dir).items():
            rows = db.cursor().execute("SELECT * FROM titles WHERE (id = ?) OR (id LIKE ?);", (arc["id"], arc["id"] + '--%',)).fetchall()
            if not rows:
                print("• No DB entry:", arc["archive_path"])
                print(arc["id"])
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
                else:
                    manifest_path = manifest_path_for_archive(titles_dir, manifests_dir, util.path(titles_dir, r["archive_path"]))
                    if not util.is_file(manifest_path):
                        missing_manifests.append(manifest_path)
                if not util.is_file("data/img/" + r["id"] + ".iff"):
                    missing_images.append(r["id"])
            if missing_archives:
                print("• Titles missing archives:")
                for id in missing_archives:
                    print("{}".format(id))
                print()
            if missing_images:
                print("• Titles missing images:")
                for id in missing_images:
                    print("{}".format(id))
                print()
            if missing_manifests:
                print("• Missing manifests (generate with 'make missing-manifests'):")
                for id in missing_manifests:
                    print("{}".format(id))
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
