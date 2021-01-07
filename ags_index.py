#!/usr/bin/env python3

# AGSImager: Indexer

# WHDLoad packs available at
# http://tinyurl.com/m9qjwpy
#  -> https://mega.nz/#F!gdozjZxL!uI5SheetsAd-NYKMeRjf2A

import argparse
import os
import sqlite3
import sys

from lhafile import LhaFile
import ags_util as util

TITLES_DIR = "../AGSImager-Content/titles/"

# -----------------------------------------------------------------------------
# Make dictionary of whdload archives

def index_whdload_archives(basedir):
    print("enumerating archives..", end="", flush=True)
    count = 0
    d = {}
    for r, _, f in os.walk(basedir):
        for file in f:
            if file.endswith(".lha"):
                count += 1
                if count % 100 == 0:
                    print(".", end="", flush=True)
                path = os.path.join(r, file)
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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--make-sqlite", dest="make_sqlite", action="store_true", default=False, help="make sqlite db from cvs, if none none exists or if cvs is newer than existing")
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", default=False, help="verbose output")

    try:
        args = parser.parse_args()
        db = util.get_db(args.verbose)

        if args.make_sqlite:
            db.close()
            return 0

        if not util.is_dir(TITLES_DIR):
            raise IOError("titles dir missing:", TITLES_DIR)

        # remove missing archive_paths from db
        for r in db.cursor().execute("SELECT * FROM titles"):
            if r["archive_path"] and not util.is_file(os.path.join(TITLES_DIR, r["archive_path"])):
                print("archive removed:", r["id"])
                print("  >>", r["archive_path"])
                db.cursor().execute("UPDATE titles SET archive_path=NULL,slave_path=NULL,slave_version=NULL WHERE id=?;", (r["id"],))
                print()

        # enumerate whdl archives, correlate with db
        for _, arc in index_whdload_archives(TITLES_DIR).items():
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

        # list more missing stuff
        if args.verbose:
            for r in db.cursor().execute("SELECT * FROM titles"):
                if not util.is_file("data/img/" + r["id"] + ".iff"):
                    print("missing image:", r["id"])
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
