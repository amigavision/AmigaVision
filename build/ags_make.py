#!/usr/bin/env python3

# AGSImager: Make AGS entries

import operator
import shutil
import sys
import textwrap
from pathlib import Path
from sqlite3 import Connection
from time import perf_counter

import ags_compositor as compositor
import ags_paths as paths
import ags_query as query
import ags_util as util
from ags_strings import strings
from ags_types import EntryCollection
from make_vadjust import VSHIFT_MAX, VSHIFT_MIN

AGS_INFO_WIDTH = 54
AGS_LIST_WIDTH = 30
MAX_FILENAME_LENGTH = 96
WARNED_MISSING_ARCHIVES = set()

# -----------------------------------------------------------------------------

def print_warning(message: str):
    print("")
    print(" > WARNING: {}".format(message))

def reset_warning_state():
    WARNED_MISSING_ARCHIVES.clear()

def warn_missing_archive(name: str, archive_path: str):
    if archive_path in WARNED_MISSING_ARCHIVES:
        return
    print_warning("missing archive for {} ({})".format(name, archive_path))
    WARNED_MISSING_ARCHIVES.add(archive_path)

def count_tree_entries(node):
    total = 0
    if isinstance(node, list):
        for item in node:
            if isinstance(item, str):
                total += 1
            elif isinstance(item, list):
                total += count_tree_entries(item)
            elif isinstance(item, dict):
                for _, value in item.items():
                    if not isinstance(value, dict):
                        total += count_tree_entries(value)
    return total


def update_progress(collection: EntryCollection, verbose: bool):
    if verbose and collection.progress_total > 0:
        print(
            "\r > Building AGS2 tree [{}/{}]".format(collection.progress_current, collection.progress_total),
            end="",
            flush=True
        )

def add_timing(collection: EntryCollection, label: str, duration: float):
    collection.timing[label] = collection.timing.get(label, 0.0) + duration

def make_canonical_name(entry) -> str | None:
    max_len = MAX_FILENAME_LENGTH - 5
    if not (isinstance(entry, dict)):
        return None
    entry_id = entry.get("id")
    if entry_id:
        # These filenames are internal runscript paths, so prefer the stable
        # unique database id over display-oriented names that can collide.
        return sanitize_name(entry_id).replace("#", "")[:max_len].strip()

    name = sanitize_name(entry.get("title_short") or entry.get("title") or "")
    return name.replace("#", "")[:max_len].strip() or None

def sanitize_name(name: str) -> str:
    name = name.replace("/", "-").replace("\\", "-").replace(": ", " ").replace(":", " ").replace("\"", "")
    if name[0] == '(':
        name = name.replace('(', '[', 1).replace(')', ']', 1)
    return name.strip()

def wrap_note(text: str) -> str:
    wrapped = []
    for line in text.replace("\\n", "\n").splitlines():
        if not line.strip():
            wrapped.append("")
        elif line != line.strip():
            # Preserve intentionally padded lines exactly as authored.
            wrapped.append(line)
        else:
            wrapped.append(textwrap.fill(line, AGS_INFO_WIDTH))
    return "\n".join(wrapped)

def normalize_release_year(release_date: str) -> tuple[str, str]:
    year, _, _ = util.parse_date(release_date or "")
    year = (year or "").strip()
    if not year:
        return "Unknown", "19XX"
    if "x" in year.lower():
        return "Unknown", "19XX"
    return year, year

def make_image(path, options):
    if util.is_file(path):
        return
    size = (320, 256)
    scale = (1, 0.5)
    if isinstance(options, dict) and "ops" in options:
        if "size" in options:
            size = (options["size"][0], options["size"][1])
        if "scale" in options:
            scale = (options["scale"][0], options["scale"][1])
        operations = options["ops"]
    else:
        operations = options
    compositor.out_iff(path, compositor.compose(operations, size=size), scale=scale)

def get_extra_image_paths(entry_id: str) -> list[tuple[Path, str]]:
    extra = []

    base_image = Path(util.path("data", "img", entry_id + ".iff"))
    if base_image.is_file():
        extra.append((base_image, ".iff"))

    for img_path in Path(util.path("data", "img")).rglob(entry_id + "-[0-9].iff"):
        suffix = img_path.stem.rsplit(entry_id, 1)[-1] + ".iff"
        extra.append((img_path, suffix))

    qr_image = Path(util.path("data", "img", "qr", entry_id + "-qr.iff"))
    if qr_image.is_file():
        extra.append((qr_image, "-QR.iff"))

    return extra

# -----------------------------------------------------------------------------
# create entries from dictionary/tree

def make_tree(
        db: Connection, collection: EntryCollection, ags_path, node,
        path=[], template=None, hidden=False, verbose=False
    ):
    if isinstance(node, list):
        entries = []
        image = None
        note = None
        ordering = None
        rank = None

        for item in node:
            # plain title
            if isinstance(item, str):
                entries += [item]
            # list
            if isinstance(item, list):
                for e in item:
                    if isinstance(e, dict):
                        make_tree(db, collection, ags_path, [e], path, template=template, hidden=hidden, verbose=verbose)
                    else:
                        raise ValueError("make_tree: list error ({})".format(e))
            # parse metadata or subtree
            if isinstance(item, dict):
                if "image" in item:
                    image = item.pop("image")
                if "note" in item:
                    note = str(item.pop("note"))
                if "ordering" in item:
                    ordering = item.pop("ordering")
                if "rank" in item:
                    rank = item.pop("rank")
                for key, value in item.items():
                    if isinstance(value, dict):
                        # item has override options
                        entries += [(key, value)]
                    else:
                        # item is a subtree
                        hidden = hidden or item.get("hidden", False)
                        make_tree(db, collection, ags_path, value, path + [key], template=template, hidden=hidden, verbose=verbose)
        make_entries(db, collection, ags_path, entries, path, note=note, image=image, ordering=ordering, rank=rank, template=template, hidden=hidden, verbose=verbose)

# -----------------------------------------------------------------------------
# create entries from list

def make_entries(
        db: Connection, collection: EntryCollection, ags_path, entries, path,
        note=None, image=None, ordering=None, rank=None, template=None, hidden=False, verbose=False
    ):
    # make dir
    base_path = ags_path
    if path:
        for d in path:
            base_path = util.path(base_path, d[:AGS_LIST_WIDTH].strip() + ".ags")
    if not hidden: util.make_dir(base_path)

    # set dir sort rank
    if rank is not None:
        collection.path_sort_rank[base_path] = rank

    # make note, image
    if not hidden:
        if note:
            note = wrap_note(note)
            open(base_path[:-4] + ".txt", mode="w", encoding="latin-1", errors="replace").write(note)
        if isinstance(image, (dict, list)):
            make_image(base_path[:-4] + ".iff", image)

    # collect titles
    pos = 0
    for name in entries:
        pos += 1
        n = name
        options = None
        if isinstance(name, tuple) and len(name) == 2 and isinstance(name[1], dict):
            n = name[0]
            options = name[1]

        # use preferred entry if found, except when name was ID-like
        lookup_start = perf_counter()
        entry, pref_entry = query.get_entry(db, n)
        add_timing(collection, "menu lookup", perf_counter() - lookup_start)
        if pref_entry and query.name_is_fuzzy(n): entry = pref_entry
        if not entry:
            missing_entry = query.get_missing_archive_entry(db, n)
            if missing_entry:
                archive_path = missing_entry["archive_path"]
                warn_missing_archive(n, archive_path)
                continue
            if options is None or (options and not options.get("unavailable", False)):
                print_warning("invalid entry: {}".format(n))
                continue
            else:
                disp_name = n.replace("-", " ")
                entry = { "id": n, "title": disp_name, "title_short": disp_name, "unavailable": True }
        if entry:
            collection.by_id[entry["id"]] = entry

        rank = str(pos).zfill(len(str(len(entries)))) if ordering == "ranked" else None

        sort_rank = None
        if ordering == "ordered":
            sort_rank = pos
        elif ordering == "release" and entry and "release_date" in entry:
            sort_rank = util.parse_date_int(entry["release_date"], sortable=True)

        if hidden: continue

        entry_start = perf_counter()
        make_entry(collection, ags_path, entry, base_path, rank=rank, sort_rank=sort_rank, options=options, template=template)
        add_timing(collection, "menu make_entry", perf_counter() - entry_start)
        collection.progress_current += 1
        update_progress(collection, verbose)
    return

# -----------------------------------------------------------------------------
# create entry

def make_entry(collection: EntryCollection, ags_path, entry, path, rank=None, sort_rank=None, prefix=None, options=None, template=None):
    max_w = AGS_LIST_WIDTH
    runfile_ext = ".run"
    note = None

    if not isinstance(entry, dict):
        raise ValueError("make_entry: no entry dict")

    entry = entry.copy()

    if entry.get("note", None):
        note = entry["note"]

    # apply override options
    has_overrides = False
    if isinstance(options, dict):
        if "id" in options or "title_short" in options:
            raise ValueError("make_entry: illegal key(s) in override options ({})".format(str(options)))
        if "scale" in options or "vshift" in options or "hshift" in options or "slave_args" in options:
            has_overrides = True
        entry.update(options)

    # skip if entry already added at path
    path_id = (entry["id"], path)
    if path_id in collection.path_ids:
        return
    else:
        collection.path_ids.add(path_id)

    # fix path name
    path_prefix = ags_path
    if path != path_prefix:
        path_suffix = path.split(path_prefix + "/")[-1]
        path = path_prefix + "/" + "/".join(list(map(sanitize_name, path_suffix.split("/"))))

    # base name
    title = rank + " " if rank else ""
    if prefix:
        title = prefix + " - " + title

    # prettify name
    disp_name = entry["disp_name"] if "disp_name" in entry else entry["title_short"]
    title += sanitize_name(disp_name)

    # shorten name and prevent name clashes
    title = title.strip()
    if len(title) > max_w: title = title.replace(", The", "")

    if util.is_file(util.path(path, title) + runfile_ext):
        if entry.get("category", "").lower() == "demo":
            title += " (" + entry.get("publisher") + ")"
        else:
            # add language prefix and/or hardware info
            title = title.rstrip() + " (" + query.get_hardware_short(entry) + ")"
            if util.is_file(util.path(path, title) + runfile_ext):
                languages = query.get_languages(entry)
                if len(languages) == 1:
                    title = title.rstrip() + " [" + util.language_code(languages[0]).upper() + "]"

    if len(title) > max_w: title = title.replace("(", "").replace(")", "")

    if len(title) > max_w:
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
    if has_overrides:
        if not template:
            raise IOError("make_entry: no run script template")
        runfile = make_runscript(entry, template, False)
    else:
        runfile = "execute \"AGS:{}/{}\"".format(query.get_runscript_paths(entry)[0], make_canonical_name(entry))

    if runfile:
        runfile_dest_path = base_path + runfile_ext
        if util.is_file(runfile_dest_path):
            print(" > WARNING: name clash for", entry["id"], "at", runfile_dest_path)
        else:
                open(runfile_dest_path, mode="w", encoding="latin-1", errors="replace").write(runfile)

    # apply sorting overrides
    if options and "rank" in options:
        collection.path_sort_rank["{}.run".format(base_path)] = options["rank"]
    elif sort_rank is not None:
        collection.path_sort_rank["{}.run".format(base_path)] = sort_rank

    # make note
    if options and options.get("unavailable", False):
        note = strings["note"]["title"] + entry["title"] + "\n\n" + strings["note"]["unavailable"]
        open(base_path + ".txt", mode="w", encoding="latin-1", errors="replace").write(note)
    elif entry:
        open(base_path + ".txt", mode="w", encoding="latin-1", errors="replace").write(make_note(entry, note))

    # make image
    if entry and "image" in entry:
        make_image(base_path + ".iff", entry["image"])
    elif entry and "id" in entry:
        for img_path, suffix in get_extra_image_paths(entry["id"]):
            src_path = str(img_path.resolve())
            if util.is_file(src_path):
                dst_path = base_path + suffix
                shutil.copyfile(src_path, dst_path)

    # make title metadata
    if query.entry_is_valid(entry):
        metadata = dict()
        meta_title = sanitize_name(entry["title_short"])
        unshortened_title = meta_title
        if len(meta_title) > max_w:
            meta_title = meta_title.replace(", The", "")
        if len(meta_title) > max_w:
            meta_title = meta_title[:max_w - 2].strip() + ".."
        if meta_title != unshortened_title:
            metadata["title"] = meta_title
        if entry["category"] and entry["category"] != "Game":
            if entry.get("subcategory", "").lower().startswith("music disk"):
                metadata["category"] = "Music Disk"
            elif entry.get("subcategory", "").lower().startswith("disk mag"):
                metadata["category"] = "Disk Magazine"
            elif entry.get("subcategory", "").lower().startswith("slide show"):
                metadata["category"] = "Slide Show"
            else:
                metadata["category"] = entry["category"]
        if "title" in metadata or "category" in metadata:
            if not "title" in metadata: metadata["title"] = meta_title
            tmd = metadata["title"]
            if "category" in metadata: tmd += "\n{}".format(metadata["category"])
            open(base_path + ".tmd", mode="w", encoding="latin-1", errors="replace").write(tmd)

    return base_path

# -----------------------------------------------------------------------------
# create note from entry

def make_note(entry, add_note):
    max_w = AGS_INFO_WIDTH
    note = ""
    system = entry["hardware"].replace("/", "·")
    aspect_ratio = None

    def trunc(s: str) -> str:
        if len(s) > max_w:
            s = s[:max_w - 2].strip() + ".."
        return s

    if entry.get("ntsc", 0) == 4:
        if entry.get("scale", 0) == 6:
            system += "·6×NTSC"
            aspect_ratio = "16:9"
        else:
            system += "·5×NTSC"
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

    if entry.get("lightgun", False):
        system += "·Light Gun"
    elif entry.get("gamepad", False):
        system += "·Game Pad"
    if aspect_ratio:
        system += " ({})".format(aspect_ratio)

    if "category" in entry and entry["category"].lower() == "game":
        note += trunc("{}{}".format(strings["note"]["title"], entry["title"])) + "\n"
        note += trunc("{}{}".format(strings["note"]["developer"], entry["developer"])) + "\n"
        note += trunc("{}{}".format(strings["note"]["publisher"], entry["publisher"])) + "\n"
        note += ("{}{}".format(strings["note"]["release_date"], entry["release_date"]))[:max_w] + "\n"
        note += ("{}{}".format(strings["note"]["players"], entry["players"]))[:max_w] + "\n"
        if entry.get("language"):
            language = util.prettify_names(entry["language"])
            note += trunc("{}{}".format(strings["note"]["language"], language)) + "\n"
        note += ("{}{}".format(strings["note"]["system"], system))[:max_w] + "\n"
        if entry.get("issues"):
            note += trunc("{}{}".format(strings["note"]["issues"], entry["issues"])) + "\n"
        elif entry.get("hack"):
            note += trunc("{}{}".format(strings["note"]["hack"], entry["hack"])) + "\n"

    elif "category" in entry and entry["category"].lower() == "demo":
        group = util.prettify_names(entry["publisher"])
        note += ("{}{}".format(strings["note"]["title"], entry["title"]))[:max_w] + "\n"
        note += ("{}{}".format(strings["note"]["group"], group))[:max_w] + "\n"
        if entry.get("country"):
            country = util.prettify_names(entry["country"])
            note += trunc("{}{}".format(strings["note"]["country"], country)) + "\n"
        note += ("{}{}".format(strings["note"]["release_date"], entry["release_date"]))[:max_w] + "\n"
        if entry.get("subcategory", "").lower() != "demo":
            note += ("{}{}".format(strings["note"]["category"], entry["subcategory"]))[:max_w] + "\n"
        else:
            note += "{}Demo\n".format(strings["note"]["category"])
        note += ("{}{}".format(strings["note"]["system"], system))[:max_w] + "\n"
        if entry.get("issues"):
            note += trunc("{}{}".format(strings["note"]["issues"], entry["issues"])) + "\n"

    if add_note and isinstance(add_note, str):
            note += trunc("{}{}".format(strings["note"]["note"], add_note)) + "\n"
    elif entry.get("note"):
            note += trunc("{}{}".format(strings["note"]["note"], entry["note"])) + "\n"
    return note

# -----------------------------------------------------------------------------
# make run scripts

def make_runscripts(collection: EntryCollection, ags_path: str, template=None):
    for _, entry in collection.by_id.items():
        name = make_canonical_name(entry)
        dest_paths = query.get_runscript_paths(entry)
        if dest_paths[0]:
            script = make_runscript(entry, template, False)
            dest = util.path(ags_path, dest_paths[0], name)
            util.make_dir(util.path(ags_path, dest_paths[0]))
            if util.is_file(dest):
                print(" > WARNING: duplicate script at", dest, entry["id"])
            else:
                open(dest, mode="w", encoding="latin-1", errors="replace").write(script)
        if dest_paths[1]:
            script = make_runscript(entry, template, True)
            dest = util.path(ags_path, dest_paths[1], name)
            util.make_dir(util.path(ags_path, dest_paths[1]))
            if util.is_file(dest):
                print(" > WARNING: duplicate script at", dest, entry["id"])
            else:
                open(dest, mode="w", encoding="latin-1", errors="replace").write(script)

def make_runscript(entry, template, quiet: bool) -> str:
    script = None
    if query.get_amiga_whd_dir(entry) is not None or query.entry_is_notwhdl(entry):
        # videomode
        whd_vmode = "NTSC" if util.parse_int(entry.get("ntsc", 0)) > 0 else "PAL"
        # scale
        vadjust_scale = util.parse_int(entry.get("scale", 0))
        # vertical shift
        vadjust_vshift = util.parse_int(entry.get("vshift", 0))
        vadjust_vshift = min(max(vadjust_vshift, VSHIFT_MIN), VSHIFT_MAX)
        # horizontal shift
        vadjust_hshift = util.parse_int(entry.get("hshift", 0))
        # jim sachs mode
        vadjust_sachs = "JS" if util.parse_int(entry.get("ntsc", 0)) == 4 else ""
        if not vadjust_scale: vadjust_scale = 0

        if query.entry_is_notwhdl(entry):
            archive_path = query.get_archive_path(entry)
            if archive_path:
                runfile_source_path = util.path(paths.tracked_titles(), entry["archive_path"]).replace(".lha", ".run")
                if util.is_file(runfile_source_path):
                    script = "ags-notify TITLE=\"{}\"\n".format(entry.get("title", "Unknown"))
                    script += "set{}\n".format(whd_vmode.lower())
                    script += "ags-vadjust s={} v={} h={} {}\n".format(vadjust_scale, vadjust_vshift, vadjust_hshift, vadjust_sachs)
                    with open(runfile_source_path, 'r') as f: script += f.read()
                    script += "setvmode $AGSVMode\n"
                    script += "ags-vadjust\n"
                    script += "ags-notify\n"
                else:
                    script = "echo \"Title not available.\"" + "\n" + "wait 2"
            else:
                script = "echo \"Title not available.\"" + "\n" + "wait 2"
        else:
            archive_path = query.get_archive_path(entry)
            if archive_path:
                whd_entrypath = query.get_amiga_whd_dir(entry)
                if whd_entrypath:
                    whd_cargs = "BUTTONWAIT"
                    if entry.get("slave_args"):
                        whd_cargs += " " + entry["slave_args"]
                    whd_qtkey = "" if "QuitKey=" in whd_cargs else "$whdlqtkey"
                    whd_spdly = "0" if quiet else "$whdlspdly"
                    script = util.apply_template(template, {
                        "TITLE": entry.get("title", "Unknown"),
                        "PATH": whd_entrypath,
                        "SLAVE": query.get_whd_slavename(entry),
                        "CUST_ARGS": whd_cargs,
                        "QUIT_KEY": whd_qtkey,
                        "SPLASH_DELAY": whd_spdly,
                        "VIDEO_MODE": whd_vmode,
                        "VADJUST_SCALE": vadjust_scale,
                        "VADJUST_VSHIFT": vadjust_vshift,
                        "VADJUST_HSHIFT": vadjust_hshift,
                        "VADJUST_SACHS": vadjust_sachs
                    })
            else:
                script = "echo \"Title not available.\"" + "\n" + "wait 2"
    else:
        script = "echo \"Title not available.\"" + "\n" + "wait 2"

    if entry and util.parse_int(entry.get("killaga", 0)) > 0:
        tmp = ""
        for line in script.splitlines():
            if "whdload >NIL: " in line:
                line = line.replace('"', '') .replace('whdload >NIL: ', 'killaga "whdload ') + '" >NIL:'
            tmp += line + "\n"
        script = tmp

    return script

# -----------------------------------------------------------------------------
# collect entries for special folders ("All Games", "Demo Scene")

def make_autoentries(c: EntryCollection, path: str, games=False, demos=False):
    d_path = util.path(path, "{}.ags".format(strings["dirs"]["scene"]))
    ne_path = util.path(path, "{}.ags".format(strings["dirs"]["allgames_nonenglish"]))
    created_images = set()

    def ensure_image(path, options):
        if path in created_images:
            return
        created_images.add(path)
        make_image(path, options)

    for entry in sorted(c.ids(), key=operator.itemgetter("title_short")):
        if entry.get("unavailable", False):
            c.progress_current += 1
            continue
        letter = entry.get("title_short", "z")[0].upper()
        if letter.isnumeric():
            letter = "#"
        year, year_img = normalize_release_year(entry.get("release_date", ""))

        # add games
        if games and entry.get("category", "").lower() == "game":
            if query.has_english_language(entry):
                start = perf_counter()
                make_entry(c, path, entry, util.path(path, "{}.ags".format(strings["dirs"]["allgames"]), letter + ".ags"))
                add_timing(c, "auto make_entry", perf_counter() - start)
                ensure_image(util.path(path, "{}.ags".format(strings["dirs"]["allgames"]), letter + ".iff"), {"op":"tx", "txt": letter})
                start = perf_counter()
                make_entry(c, path, entry, util.path(path, "{}.ags".format(strings["dirs"]["allgames_year"]), year + ".ags"))
                add_timing(c, "auto make_entry", perf_counter() - start)
                ensure_image(util.path(path, "{}.ags".format(strings["dirs"]["allgames_year"]), year + ".iff"), {"op":"tx", "txt": year_img, "size": 112})
            languages = query.get_languages(entry)
            for language in languages:
                if language.lower() != "english":
                    start = perf_counter()
                    make_entry(c, path, entry, util.path(ne_path, language + ".ags"))
                    add_timing(c, "auto make_entry", perf_counter() - start)
                    flag_path = "flags/{}.png".format(util.country(language).lower())
                    img_ops =  { "ops": { "op": "pi", "path": flag_path }, "size": [320, 128 ], "scale": [1, 1] }
                    ensure_image(util.path(ne_path, language + ".iff"), img_ops)
            if languages and not query.has_english_language(entry) and not entry.get("preferred_version", None):
                start = perf_counter()
                make_entry(c, ne_path, entry, util.path(ne_path, "{}.ags".format(strings["dirs"]["unique_nonenglish"])))
                add_timing(c, "auto make_entry", perf_counter() - start)
                img_ops =  { "ops": { "op": "pi", "path": "flags/eu barcode.png" }, "size": [320, 128 ], "scale": [1, 1] }
                ensure_image(util.path(ne_path, strings["dirs"]["unique_nonenglish"] + ".iff"), img_ops)

        # add demos, disk mags, etc
        def add_demo(entry, sort_group, sort_country):
            if sort_group.startswith("The "):
                sort_group = sort_group[4:]
            sort_group = sort_group[:AGS_LIST_WIDTH]
            group_letter = sort_group[0].upper()
            if group_letter.isnumeric():
                group_letter = "#"
            if entry.get("subcategory", "").lower().startswith("disk mag"):
                start = perf_counter()
                make_entry(c, path, entry, util.path(d_path, "{}.ags".format(strings["dirs"]["diskmags"])))
                add_timing(c, "auto make_entry", perf_counter() - start)
                start = perf_counter()
                mag_path = make_entry(c, path, entry, util.path(d_path, "{}.ags".format(strings["dirs"]["diskmags_date"])))
                add_timing(c, "auto make_entry", perf_counter() - start)
                if mag_path:
                    rank = util.parse_date_int(entry["release_date"], sortable=True)
                    c.path_sort_rank["{}.run".format(mag_path)] = rank if rank else 0
            elif entry.get("subcategory", "").lower().startswith("music disk"):
                start = perf_counter()
                make_entry(c, path, entry, util.path(d_path, "{}.ags".format(strings["dirs"]["musicdisks"]), letter + ".ags"))
                add_timing(c, "auto make_entry", perf_counter() - start)
                ensure_image(util.path(d_path, "{}.ags".format(strings["dirs"]["musicdisks"]), letter + ".iff"), {"op":"tx", "txt": letter})
                start = perf_counter()
                make_entry(c, path, entry, util.path(d_path, "{}.ags".format(strings["dirs"]["musicdisks_year"]), year + ".ags"))
                add_timing(c, "auto make_entry", perf_counter() - start)
                ensure_image(util.path(d_path, "{}.ags".format(strings["dirs"]["musicdisks_year"]), year + ".iff"), {"op":"tx", "txt": year_img, "size": 112})
            elif entry.get("subcategory", "").lower().startswith("slide"):
                start = perf_counter()
                make_entry(c, path, entry, util.path(d_path, "{}.ags".format(strings["dirs"]["slideshows"])))
                add_timing(c, "auto make_entry", perf_counter() - start)
            else:
                if entry.get("subcategory", "").lower().startswith("crack"):
                    start = perf_counter()
                    make_entry(c, path, entry, util.path(d_path, "{}.ags".format(strings["dirs"]["demos_cracktro"])), prefix=sort_group)
                    add_timing(c, "auto make_entry", perf_counter() - start)
                if entry.get("subcategory", "").lower().startswith("intro"):
                    start = perf_counter()
                    make_entry(c, path, entry, util.path(d_path, "{}.ags".format(strings["dirs"]["demos_intro"])))
                    add_timing(c, "auto make_entry", perf_counter() - start)
                group_entry = dict(entry)
                group_entry["disp_name"] = group_entry.get("title")
                start = perf_counter()
                make_entry(c, path, entry, util.path(d_path, "{}.ags".format(strings["dirs"]["demos"]), letter + ".ags"))
                add_timing(c, "auto make_entry", perf_counter() - start)
                ensure_image(util.path(d_path, "{}.ags".format(strings["dirs"]["demos"]), letter + ".iff"), {"op":"tx", "txt": letter})
                start = perf_counter()
                make_entry(c, path, group_entry, util.path(d_path, "{}.ags".format(strings["dirs"]["demos_group"]), group_letter + ".ags"), prefix=sort_group)
                add_timing(c, "auto make_entry", perf_counter() - start)
                ensure_image(util.path(d_path, "{}.ags".format(strings["dirs"]["demos_group"]), group_letter + ".iff"), {"op":"tx", "txt": group_letter})
                start = perf_counter()
                make_entry(c, path, entry, util.path(d_path, "{}.ags".format(strings["dirs"]["demos_year"]), year + ".ags"))
                add_timing(c, "auto make_entry", perf_counter() - start)
                ensure_image(util.path(d_path, "{}.ags".format(strings["dirs"]["demos_year"]), year + ".iff"), {"op":"tx", "txt": year_img, "size": 112})
                if sort_country:
                    start = perf_counter()
                    make_entry(c, path, entry, util.path(d_path, "{}.ags".format(strings["dirs"]["demos_country"]), sort_country + ".ags"))
                    add_timing(c, "auto make_entry", perf_counter() - start)
                    flag_path = "flags/{}.png".format(sort_country.lower())
                    img_ops =  { "ops": { "op": "pi", "path": flag_path }, "size": [320, 128 ], "scale": [1, 1] }
                    ensure_image(util.path(d_path, "{}.ags".format(strings["dirs"]["demos_country"]), sort_country + ".iff"), img_ops)

        if demos and entry.get("category", "").lower() == "demo":
            groups = query.get_publishers(entry)
            if not groups:
                c.progress_current += 1
                continue
            for sort_group in groups:
                countries = query.get_countries(entry)
                if not countries:
                    add_demo(entry, sort_group, None)
                else:
                    for sort_country in countries:
                        add_demo(entry, sort_group, sort_country)
        c.progress_current += 1
        update_progress(c, True)

    # notes and images for created directories
    for dir in ["allgames", "allgames_year", "allgames_nonenglish", "scene", "issues"]:
        if util.is_dir(util.path(path, "{}.ags".format(strings["dirs"][dir]))):
            open(util.path(path, "{}.txt".format(strings["dirs"][dir])), mode="w", encoding="latin-1", errors="replace").write(wrap_note(strings["desc"][dir]))
            img_src = util.path("top", strings["images"][dir])
            if util.is_file("{}{}".format(compositor.IMG_SRC_BASE, img_src)):
                make_image(util.path(path, "{}.iff".format(strings["dirs"][dir])), {"ops":{"op":"pi", "path":img_src}, "size":[320,128], "scale":[1,1]})

    for dir in [
        "demos", "demos_country", "demos_group", "demos_year", "demos_cracktro", "demos_intro",
        "diskmags", "diskmags_date", "musicdisks", "musicdisks_year", "slideshows"
    ]:
        if util.is_dir(util.path(d_path, "{}.ags".format(strings["dirs"][dir]))):
            open(util.path(d_path, "{}.txt".format(strings["dirs"][dir])), mode="w", encoding="latin-1", errors="replace").write(wrap_note(strings["desc"][dir]))

    for dir in ["unique_nonenglish"]:
        if util.is_dir(util.path(ne_path, "{}.ags".format(strings["dirs"][dir]))):
            open(util.path(ne_path, "{}.txt".format(strings["dirs"][dir])), mode="w", encoding="latin-1", errors="replace").write(wrap_note(strings["desc"][dir]))

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("not runnable")
    sys.exit(1)
