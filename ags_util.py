#!/usr/bin/env python3

# WHDLImager utility functions

import csv
import math
import os
import shutil
import sqlite3
import stat
import sys

from ruamel import yaml
from lhafile import LhaFile

# -----------------------------------------------------------------------------
# Utility functions

def merge(src, dst):
    for key, value in src.items():
        if isinstance(value, dict):
            node = dst.setdefault(key, {})
            merge(value, node)
        else:
            dst[key] = value
    return dst

def merge_dicts(*dicts):
    res = {}
    for d in dicts:
        res.update(d)
    return res

def remove_keys(dictionary, keys):
    d = dict(dictionary)
    for k in keys:
        d.pop(k, None)
    return d


def is_file(path):
    return os.path.isfile(path)

def is_dir(path):
    return os.path.isdir(path)

def argparse_is_file(parser, arg):
    if not os.path.isfile(arg):
        parser.error("File %s does not exist" % arg)
    else:
        return arg

def argparse_is_dir(parser, arg):
    if not os.path.isdir(arg):
        parser.error("Directory %s does not exist" % arg)
    else:
        return arg

def make_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def get_dir_size(start_path=".", block_size=1):
    file_size = 0
    path_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        path = dirpath.replace(os.path.commonprefix([dirpath, start_path]), "")
        for d in dirnames:
            path_size += len(os.path.join(path, d))
        for f in filenames:
            path_size += len(os.path.join(path, f))
            fp = os.path.join(dirpath, f)
            file_size += math.ceil(os.path.getsize(fp) / block_size) * block_size
    return (file_size, path_size, file_size + path_size)

def copytree(src, dst, symlinks=False, ignore=None):
    if not os.path.exists(dst):
        os.makedirs(dst)
        shutil.copystat(src, dst)
    lst = os.listdir(src)
    if ignore:
        excl = ignore(src, lst)
        lst = [x for x in lst if x not in excl]
    for item in lst:
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if symlinks and os.path.islink(s):
            if os.path.lexists(d):
                os.remove(d)
            os.symlink(os.readlink(s), d)
            try:
                st = os.lstat(s)
                mode = stat.S_IMODE(st.st_mode)
                os.lchmod(d, mode)
            except:
                pass
        elif os.path.isdir(s):
            copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)

# -----------------------------------------------------------------------------

def yaml_write(data, path):
    with open(path, 'w') as f:
        yaml.round_trip_dump(data, f, explicit_start=True, version=(1, 2))

def yaml_load(path):
    with open(path, 'r') as f:
        d = yaml.safe_load(f)
    return d

# -----------------------------------------------------------------------------

def lha_extract(arcpath, outpath):
    arc = LhaFile(arcpath)
    for filename in [info.filename for info in arc.infolist()]:
        path = filename.replace("\\", "/")
        dirname = os.path.dirname(path)
        basename = os.path.basename(path)
        if dirname:
            make_dir(os.path.join(outpath, dirname))
        if basename:
            make_dir(os.path.join(outpath, dirname))
            open(os.path.join(outpath, dirname, basename), "wb").write(arc.read(filename))

# -----------------------------------------------------------------------------

def get_db(verbose):
    sqlite3_path = "data/db/titles.sqlite3"
    csv_path = "data/db/titles.csv"

    update_sqlite3 = False
    if is_file(sqlite3_path):
        update_sqlite3 = os.path.getmtime(sqlite3_path) < os.path.getmtime(csv_path)
    else:
        update_sqlite3 = True

    if update_sqlite3:
        if verbose:
            print("updating title database cache...")
        read_csv(csv_path, sqlite3_path)

    db = sqlite3.connect(sqlite3_path)
    db.row_factory = sqlite3.Row
    return db


def write_csv(conn, csv_path):
    c = conn.cursor()
    c.execute("SELECT * FROM titles ORDER BY 'id' ASC")
    with open(csv_path, "w") as f:
        csv_out = csv.writer(f, delimiter=";")
        csv_out.writerow([d[0] for d in c.description])
        for result in c:
            csv_out.writerow(result)


def read_csv(csv_path, new_db_path):
    if is_file(new_db_path):
        os.remove(new_db_path)
    conn = sqlite3.connect(new_db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE "titles" (
               "id" TEXT NOT NULL UNIQUE,
               "title" TEXT,
               "title_short" TEXT,
               "redundant" INTEGER,
               "preferred_version" TEXT,
               "hardware" TEXT,
               "aga" INTEGER,
               "ntsc" INTEGER,
               "gamepad" INTEGER,
               "lightgun" INTEGER,
               "issues" TEXT,
               "hack" TEXT,
               "language" TEXT,
               "year" TEXT,
               "developer" TEXT,
               "publisher" TEXT,
               "players" TEXT,
               "slave_args" TEXT,
               "slave_version" TEXT,
               "slave_variant" TEXT,
               "slave_path" TEXT,
               "archive_path" TEXT,
               "category" TEXT,
               "subcategory" TEXT,
               "hol_id" INTEGER,
               "lemon_id" INTEGER,
               PRIMARY KEY("id"));''')

    with open(csv_path, "r") as f:
        dr = csv.DictReader(f, delimiter=";")
        r = [(l["id"], l["title"], l["title_short"], l["redundant"], l["preferred_version"], l["hardware"], l["aga"], l["ntsc"],
              l["gamepad"], l["lightgun"], l["issues"], l["hack"], l["language"], l["year"], l["developer"], l["publisher"],
              l["players"], l["slave_args"], l["slave_version"], l["slave_variant"], l["slave_path"], l["archive_path"],
              l["category"], l["subcategory"], l["hol_id"], l["lemon_id"]) for l in dr]
        c.executemany('''INSERT INTO titles (
                           id, title, title_short, redundant, preferred_version, hardware, aga, ntsc, gamepad, lightgun, issues,
                           hack, language, year, developer, publisher, players, slave_args, slave_version, slave_variant, slave_path,
                           archive_path, category, subcategory, hol_id, lemon_id)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);''', r)
    conn.commit()
    conn.close()

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("not runnable")
    sys.exit(1)
