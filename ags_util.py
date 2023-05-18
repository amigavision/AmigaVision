#!/usr/bin/env python3

# AGSImager: Utility functions

import argparse
import csv
import functools
import math
import os
import shutil
import sqlite3
import stat
import sys

from lhafile import LhaFile
from ruamel import yaml

from ags_fs import convert_filename_a2uae

# -----------------------------------------------------------------------------
# utility functions

def parse_int(v):
    try:
        return int(v)
    except ValueError:
        return 0

def parse_date(v):
    components = v.split("-")[:3]
    return components + [None] * (3 - len(components))

def parse_date_numeric(v):
    components = list(map(lambda s: int(s), v.lower().replace("x", "0").split("-")[:3]))
    return components + [None] * (3 - len(components))

def parse_date_int(v, sortable=False):
    components = list(map(lambda s: s.zfill(2), v.lower().replace("x", "0").split("-")[:3]))
    if sortable:
        return int("".join((components + 3 * ["01"])[:3]))
    else:
        return int("".join(components))

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


def path(*args) -> str:
    return os.path.expandvars(os.path.join(*args))

def is_file(path: str):
    return os.path.isfile(path)

def is_dir(path: str):
    return os.path.isdir(path)

def argparse_is_file(parser: argparse.ArgumentParser, arg: str):
    if not os.path.isfile(arg):
        parser.error("File %s does not exist" % arg)
    else:
        return arg

def argparse_is_dir(parser: argparse.ArgumentParser, arg: str):
    if not os.path.isdir(arg):
        parser.error("Directory %s does not exist" % arg)
    else:
        return arg

def make_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path)

def rm_path(path: str):
    if os.path.isfile(path):
        os.remove(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)

def get_dir_size(start_path=".", block_size=1):
    file_size = 0
    path_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        path = dirpath.replace(os.path.commonprefix([dirpath, start_path]), "")
        for d in dirnames:
            path_size += 1 + (math.ceil(len(os.path.join(path, d)) / block_size) * block_size)
        for f in filenames:
            if f.endswith(".uaem"):
                continue
            path_size += 1 + (math.ceil(len(os.path.join(path, f)) / block_size) * block_size)
            fp = os.path.join(dirpath, f)
            file_size += math.ceil(os.path.getsize(fp) / block_size) * block_size
    return file_size + path_size

def copytree(src: str, dst: str, symlinks=False, ignore=None):
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

def prettify_names(name: str):
    last_delimiter = name.rfind(", ")
    if last_delimiter > 0:
        name = name[:last_delimiter] + " & " + name[last_delimiter + 2:]
    return name

def apply_template(template: str, dictionary: dict) -> str:
    for k, v in dictionary.items():
        template = template.replace("{{" + "{}".format(k) + "}}", "{}".format(v))
    return template

# -----------------------------------------------------------------------------
# misc

def language_code(lang: str) -> str:
    codes = {
        "croatian": "hr",
        "czech": "cs",
        "danish": "da",
        "dutch": "nl",
        "english": "en",
        "finnish": "fi",
        "fremen": "fm",
        "french": "fr",
        "german": "de",
        "greek": "el",
        "hungarian": "hu",
        "italian": "it",
        "japanese": "ja",
        "norwegian": "no",
        "polish": "pl",
        "spanish": "es",
        "swedish": "sv",
    }
    if lang.lower() in codes:
        return codes[lang.lower()]
    else:
        raise ValueError("no language code for: " + lang)

def country(lang: str) -> str:
    codes = {
        "croatian": "Croatia",
        "czech": "Czech Republic",
        "danish": "Denmark",
        "dutch": "Netherlands",
        "english": "UK",
        "finnish": "Finland",
        "fremen": "Fremen",
        "french": "France",
        "german": "Germany",
        "greek": "Greece",
        "hungarian": "Hungary",
        "italian": "Italy",
        "japanese": "Japan",
        "norwegian": "Norway",
        "polish": "Poland",
        "spanish": "Spain",
        "swedish": "Sweden",
    }
    if lang.lower() in codes:
        return codes[lang.lower()]
    else:
        raise ValueError("no country name for: " + lang)

def sorted_natural(lst):
    rom_nums = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15}
    alpha_order = " !\"#$%&'()*+,-./0123456789aàáâãbcçdeèéêëfghiìíîïjklmnñoòóôõpqrsßtuùúûüvwxyýÿzåäæöø:;<=>?@[\]^_`{|}~¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿Ð×Þð÷þ"
    table_order = dict(zip(alpha_order, range(len(alpha_order))))

    def rank(c):
        if c in table_order: return table_order[c]
        return len(table_order)

    def deroman(s):
        wl = s.replace(".", "").replace(":", "").replace(";", "").split(" ")
        res = [wl.pop(0)]
        for w in wl:
            if w in rom_nums: res.append(str(rom_nums[w]))
            else: res.append(w)
        return " ".join(res)

    def rom_comp(a, b):
        if a == b: return 0
        (ra, rb) = (deroman(a), deroman(b))
        if len(ra) == 0: return -1
        if len(rb) == 0: return 1
        for x in zip(ra.lower(), rb.lower()):
            (rax, rbx) = (rank(x[0]), rank(x[1]))
            if rax == rbx: continue
            return 1 if rax > rbx else -1
        return 1 if len(ra) > len(rb) else -1

    return sorted(lst, key=functools.cmp_to_key(rom_comp))

# -----------------------------------------------------------------------------
# data extraction

def lha_extract(arcpath, outpath):
    arc = LhaFile(arcpath)
    for filename in [info.filename for info in arc.infolist()]:
        path = filename.replace("\\", "/")
        dirname = convert_filename_a2uae(os.path.dirname(path))
        basename = convert_filename_a2uae(os.path.basename(path))
        if dirname:
            make_dir(os.path.join(outpath, dirname))
        if basename:
            make_dir(os.path.join(outpath, dirname))
            open(os.path.join(outpath, dirname, basename), "wb").write(arc.read(filename))

# -----------------------------------------------------------------------------
# yaml serialization

yaml_path_stack = []

def constr_include(loader, node):
    global yaml_path_stack
    p = path(yaml_path_stack[-1], loader.construct_scalar(node))
    if not is_file(p):
        raise IOError("file not found")
    yaml_path_stack.append(os.path.dirname(os.path.abspath(p)))
    with open(p, 'r') as f:
        d = yaml.safe_load(f)
    yaml_path_stack.pop()
    return d

yaml.SafeConstructor.add_constructor(u'!include', constr_include)

def yaml_write(data, path: str):
    with open(path, 'w') as f:
        yaml.round_trip_dump(data, f, explicit_start=True, version=(1, 2))

def yaml_load(yaml_path: str):
    global yaml_path_stack
    p = path(os.getcwd(), yaml_path)
    if not is_file(p):
        raise IOError("file not found")
    yaml_path_stack.append(os.path.dirname(os.path.abspath(p)))
    with open(p, 'r') as f:
        return yaml.safe_load(f)

# -----------------------------------------------------------------------------
# database functions

def get_db(verbose: bool):
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


def write_csv():
    sqlite3_path = "data/db/titles.sqlite3"
    csv_path = "data/db/titles.csv"

    if not is_file(sqlite3_path):
        raise IOError("SQLite database doesn't exist: " + sqlite3_path)

    csv.register_dialect("megaags",
        delimiter=';',
        doublequote=True,
        escapechar=None,
        lineterminator='\n',
        quotechar='"',
        quoting=0,
        skipinitialspace=False,
        strict=False
    )

    conn = sqlite3.connect(sqlite3_path)
    c = conn.cursor()
    c.execute("SELECT * FROM titles ORDER BY 'id' ASC")
    with open(csv_path, "w") as f:
        csv_out = csv.writer(f, dialect="megaags")
        csv_out.writerow([d[0] for d in c.description])
        for result in c:
            csv_out.writerow(result)
    conn.close()
    csv.unregister_dialect("megaags")


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
               "scale" INTEGER,
               "v_offset" INTEGER,
               "killaga" INTEGER,
               "gamepad" INTEGER,
               "lightgun" INTEGER,
               "note" TEXT,
               "issues" TEXT,
               "hack" TEXT,
               "release_date" TEXT,
               "country" TEXT,
               "language" TEXT,
               "developer" TEXT,
               "publisher" TEXT,
               "players" TEXT,
               "slave_args" TEXT,
               "slave_version" TEXT,
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
              l["scale"], l["v_offset"], l["killaga"], l["gamepad"], l["lightgun"], l["note"], l["issues"], l["hack"], l["release_date"],
              l["country"], l["language"], l["developer"], l["publisher"], l["players"], l["slave_args"], l["slave_version"],
              l["slave_path"], l["archive_path"], l["category"], l["subcategory"], l["hol_id"], l["lemon_id"]) for l in dr]
        c.executemany('''INSERT INTO titles (
                           id, title, title_short, redundant, preferred_version, hardware, aga, ntsc,
                           scale, v_offset, killaga, gamepad, lightgun, note, issues, hack, release_date, country, language,
                           developer, publisher, players, slave_args, slave_version, slave_path, archive_path,
                           category, subcategory, hol_id, lemon_id)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);''', r)
    conn.commit()
    conn.close()

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("not runnable")
    sys.exit(1)
