#!/usr/bin/env python3

# AVSImager: Make AVS entries

import operator
import os
import re
import shutil
import sys
import textwrap
from pathlib import Path
from sqlite3 import Connection
from time import perf_counter

from avs_artwork import is_nsfw, install_nsfw_thumbnail
from avs_migration import rename_reference

import avs_compositor as compositor
import avs_paths as paths
import avs_query as query
import avs_util as util
from avs_strings import strings
from avs_types import EntryCollection
from make_vadjust import VSHIFT_MAX, VSHIFT_MIN

AVS_INFO_WIDTH = 48
AVS_INFO_HEIGHT = 7
AVS_LIST_WIDTH = 30
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
            "\r > Building AVS tree [{}/{}]".format(collection.progress_current, collection.progress_total),
            end="",
            flush=True
        )

def add_timing(collection: EntryCollection, label: str, duration: float):
    collection.timing[label] = collection.timing.get(label, 0.0) + duration

def directory_cache_entries(path, dirs, files, sort_ranks):
    """Configured rows first, using their literal directory and script names."""
    ranked = []
    unranked = []
    listed_files = set()
    for name in util.sorted_natural([n for n in files if n.endswith('.menuitem')]):
        filename = util.path(path, name)
        prefix = Path(filename).read_text(encoding='ascii').strip()
        label = name.removesuffix('.menuitem')
        if prefix not in {'F', 'V', 'E'}:
            raise ValueError(f'Invalid menu item: {filename}')
        if prefix == 'F' and label + '.run' not in files:
            raise FileNotFoundError(f'Configured menu script is missing: {path}/{label}.run')
        listed_files.add(label + '.run')
        row = ('F' if prefix == 'E' else prefix) + label
        if filename in sort_ranks:
            ranked.append((row, sort_ranks[filename]))
        else:
            unranked.append(row)
    for names, suffix, prefix in ((dirs, '.avs', 'D'), (files, '.run', 'F')):
        for name in util.sorted_natural([n for n in names if n.endswith(suffix) and n not in listed_files]):
            filename = util.path(path, name)
            item = prefix + name.removesuffix(suffix)
            label_path = Path(filename + ".label")
            if prefix == "D" and label_path.is_file():
                item = "A" + name.removesuffix(suffix) + "\t" + label_path.read_text(encoding="latin-1")
            if filename in sort_ranks:
                ranked.append((item, sort_ranks[filename]))
            else:
                unranked.append(item)
    for name in util.sorted_natural([n for n in files if n.endswith('.divider')]):
        filename = util.path(path, name)
        label = Path(filename).read_text(encoding='latin-1').strip()
        # Amiga E StrCopy(..., 0) leaves the previous label unchanged.
        item = 'S' + (label or ' ')
        if filename in sort_ranks:
            ranked.append((item, sort_ranks[filename]))
        else:
            unranked.append(item)
    return [item for item, _ in sorted(ranked, key=lambda item: item[1])] + unranked


def make_canonical_name(entry) -> str | None:
    max_len = MAX_FILENAME_LENGTH - 5
    if not (isinstance(entry, dict)):
        return None
    name = sanitize_name(entry["title_short"])
    meta = ""
    # add group name for demos
    if entry.get("category", "").lower() == "demo":
        groups = query.get_publishers(entry)
        if len(groups):
            meta += "(" + groups[0] + ")"
    # add hardware info
    meta += "(" + query.get_hardware_short(entry) + ")"
    # add language
    if entry.get("category", "").lower() == "game":
        languages = list(map(lambda s: util.language_code(s), query.get_languages(entry)))
        meta += "[" + "-".join(languages) + "]"
    return "{} {}".format(name, meta).replace("#", "")[:max_len].strip()

def sanitize_name(name: str) -> str:
    name = name.replace("/", "-").replace("\\", "-").replace(": ", " ").replace(":", " ").replace("\"", "")
    if name[0] == '(':
        name = name.replace('(', '[', 1).replace(')', ']', 1)
    return name.strip()

def wrap_note(text: str) -> str:
    wrapped = []
    for line in text.replace("\\\\n", "\n").replace("\\n", "\n").strip("\n").splitlines():
        if not line.strip():
            wrapped.append("")
        else:
            wrapped.extend(balanced_wrap(line.strip()))
    if len(wrapped) > AVS_INFO_HEIGHT:
        print_warning("launcher description exceeds {} lines: {}".format(AVS_INFO_HEIGHT, text.strip()[:60]))
        wrapped = wrapped[:AVS_INFO_HEIGHT]
        wrapped[-1] = wrapped[-1][:AVS_INFO_WIDTH - 2].rstrip(" .") + ".."
    if wrapped and len(wrapped) < AVS_INFO_HEIGHT:
        wrapped.insert(0, "")
    return "\n".join(line.center(AVS_INFO_WIDTH).rstrip() if line else "" for line in wrapped)

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

def prepare_menu_ordering(node):
    """Expand declared-order menus into automatic ranks before subtree caching.

    Ranks remain an internal build detail. Unlisted/generated entries retain
    their existing ordering and sort after the configured entries.
    """
    if not isinstance(node, list):
        return node

    def flatten(rows):
        for row in rows:
            if isinstance(row, list):
                yield from flatten(row)
            else:
                yield row

    def without_parent_ranks(rows):
        result = []
        for row in rows:
            if isinstance(row, list):
                result.append(without_parent_ranks(row))
            elif isinstance(row, dict):
                row = {key: value for key, value in row.items() if key != 'rank'}
                if row:
                    result.append(row)
            else:
                result.append(row)
        return result

    expanded = list(flatten(node))
    declared = any(isinstance(row, dict) and row.get('ordering') == 'declared'
                   for row in expanded)
    metadata = {'image', 'note', 'ordering', 'rank', 'hidden', 'label'}
    result = []
    position = 0
    for row in expanded if declared else node:
        if isinstance(row, str):
            position += 1
            result.append({row: {'rank': position}} if declared else row)
            continue
        if isinstance(row, list):
            result.append(prepare_menu_ordering(row))
            continue
        if not isinstance(row, dict):
            result.append(row)
            continue
        updated = {}
        for key, value in row.items():
            if key == 'ordering' and value == 'declared':
                continue
            if key in metadata:
                updated[key] = value
                continue
            position += 1
            if isinstance(value, list):
                child = prepare_menu_ordering(value)
                if declared:
                    child = [{'rank': position}] + without_parent_ranks(child)
                updated[key] = child
            elif isinstance(value, dict):
                updated[key] = dict(value)
                if declared:
                    updated[key]['rank'] = position
            else:
                updated[key] = value
        if updated:
            result.append(updated)
    return result


def make_tree(
        db: Connection, collection: EntryCollection, avs_path, node,
        path=[], template=None, hidden=False, verbose=False
    ):
    if isinstance(node, list):
        entries = []
        image = None
        note = None
        ordering = None
        rank = None
        label = None

        for item in node:
            # plain title
            if isinstance(item, str):
                entries += [item]
            # list
            if isinstance(item, list):
                for e in item:
                    if isinstance(e, dict):
                        make_tree(db, collection, avs_path, [e], path, template=template, hidden=hidden, verbose=verbose)
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
                if "label" in item:
                    label = item.pop("label")
                if "rank" in item:
                    rank = item.pop("rank")
                for key, value in item.items():
                    if isinstance(value, dict) and any(value.get(k) for k in ('file', 'favorites', 'exit')):
                        if not hidden:
                            make_menu_item(collection, avs_path, path, key, value)
                    elif isinstance(value, dict) and value.get("divider"):
                        if not hidden:
                            make_divider(collection, avs_path, path, key, value)
                    elif isinstance(value, dict):
                        # item has override options
                        entries += [(key, value)]
                    else:
                        # item is a subtree
                        hidden = hidden or item.get("hidden", False)
                        make_tree(db, collection, avs_path, value, path + [key], template=template, hidden=hidden, verbose=verbose)
        make_entries(db, collection, avs_path, entries, path, note=note, image=image, ordering=ordering, rank=rank, label=label, template=template, hidden=hidden, verbose=verbose)

# -----------------------------------------------------------------------------
def make_menu_item(collection, avs_path, path, name, options):
    """Place a literal file or virtual Favorites/Exit row in declaration order."""
    unknown = set(options) - {'file', 'favorites', 'exit', 'rank'}
    kinds = [key for key in ('file', 'favorites', 'exit') if options.get(key)]
    if unknown or len(kinds) != 1:
        raise ValueError(f'Invalid menu item options for {name!r}: {options}')
    if not name or len(name) > AVS_LIST_WIDTH or any(c in name for c in '\r\n\t/:\\'):
        raise ValueError(f'Invalid literal menu name: {name!r}')
    name.encode('latin-1')
    base = Path(avs_path)
    for folder in path:
        base /= folder[:AVS_LIST_WIDTH].strip() + '.avs'
    base.mkdir(parents=True, exist_ok=True)
    marker = base / (name + '.menuitem')
    marker.write_text({'file': 'F', 'favorites': 'V', 'exit': 'E'}[kinds[0]], encoding='ascii')
    if 'rank' in options:
        collection.path_sort_rank[str(marker)] = options['rank']


def make_divider(collection, avs_path, path, label, options):
    """Create a non-launchable row, with explicit rank matching folders/files."""
    unknown = set(options) - {'divider', 'rank', 'label'}
    if unknown:
        raise ValueError(f"Divider {label!r}: unsupported options {sorted(unknown)}")
    label = str(label).strip()
    if not label or any(c in label for c in '\r\n'):
        raise ValueError('Divider labels must be nonempty single lines')
    text = options.get('label', label)
    if not isinstance(text, str) or any(c in text for c in '\r\n'):
        raise ValueError('Divider label must be a single-line string (or empty)')
    text = text.strip()
    display = text
    if len(display) > AVS_LIST_WIDTH:
        raise ValueError(f'Divider exceeds {AVS_LIST_WIDTH} characters: {display}')
    display.encode('latin-1')
    base = Path(avs_path)
    for folder in path:
        base /= folder[:AVS_LIST_WIDTH].strip() + '.avs'
    base.mkdir(parents=True, exist_ok=True)
    marker_name = sanitize_name(label)
    if 'rank' in options:
        marker_name += '.' + str(options['rank'])
    marker = base / (marker_name + '.divider')
    marker.write_text(display + '\n', encoding='latin-1')
    if 'rank' in options:
        collection.path_sort_rank[str(marker)] = options['rank']


# create entries from list

def make_entries(
        db: Connection, collection: EntryCollection, avs_path, entries, path,
        note=None, image=None, ordering=None, rank=None, label=None, template=None, hidden=False, verbose=False
    ):
    # make dir
    base_path = avs_path
    if path:
        for d in path:
            base_path = util.path(base_path, d[:AVS_LIST_WIDTH].strip() + ".avs")
    if not hidden: util.make_dir(base_path)

    if label is not None and not hidden:
        if not path or not isinstance(label, str) or not label or len(label) > AVS_LIST_WIDTH or any(c in label for c in "\r\n\t"):
            raise ValueError(f"Invalid directory label: {label!r}")
        Path(base_path + ".label").write_text(label, encoding="latin-1")

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
        informational = bool(options and options.get("informational"))
        if informational:
            entry = {"id": n, "title": n, "title_short": n}
            pref_entry = None
        else:
            entry, pref_entry = query.get_entry(db, n)
        if entry and entry.get('_ecs_replaced') and isinstance(options, dict):
            # A shared list's AGA slave/video overrides do not describe its
            # replacement slave. Keep display overrides only.
            options = {k: v for k, v in options.items() if k in {'disp_name', 'note'}}
        if getattr(db, 'ecs_selector', None) and not entry:
            # Known AGA-only entries have no ECS equivalent; omit them from
            # shared menus instead of creating unavailable launch scripts.
            if next(query.iter_matching_rows(db, n), None) is not None:
                continue
        add_timing(collection, "menu lookup", perf_counter() - lookup_start)
        preferred_issue = query.get_preferred_entry_issue(db, entry)
        if preferred_issue:
            print_warning("invalid preferred version for {} ({})".format(entry["id"], preferred_issue))
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
                disp_name = options.get("disp_name") or n.replace("-", " ")
                # Human-readable unavailable menu names can still use canonical
                # game IDs for their artwork, without adding fictitious DB rows.
                slug = re.sub(r'[^a-z0-9]', '', n.lower())
                artwork_id = f'game--{slug}--{slug}'
                if not (Path('data/img', artwork_id + '.iff').is_file()
                        or Path('data/img_highres', artwork_id + '-2.iff').is_file()):
                    artwork_id = n
                entry = { "id": artwork_id, "title": disp_name, "title_short": disp_name, "unavailable": True }
        if entry and not informational:
            collection.by_id[entry["id"]] = entry

        rank = str(pos).zfill(len(str(len(entries)))) if ordering == "ranked" else None

        sort_rank = None
        if ordering == "ordered":
            sort_rank = pos
        elif ordering == "release" and entry and "release_date" in entry:
            sort_rank = util.parse_date_int(entry["release_date"], sortable=True)

        if hidden: continue

        entry_start = perf_counter()
        make_entry(collection, avs_path, entry, base_path, rank=rank, sort_rank=sort_rank, options=options, template=template)
        add_timing(collection, "menu make_entry", perf_counter() - entry_start)
        collection.progress_current += 1
        update_progress(collection, verbose)
    return

# -----------------------------------------------------------------------------
# create entry

def make_entry(collection: EntryCollection, avs_path, entry, path, rank=None, sort_rank=None, prefix=None, options=None, template=None):
    max_w = AVS_LIST_WIDTH
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
        if "note" in options:
            note = options["note"]

    # skip if entry already added at path
    path_id = (entry["id"], path)
    if path_id in collection.path_ids:
        return
    else:
        collection.path_ids.add(path_id)

    # fix path name
    path_prefix = avs_path
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
    if entry.get("informational"):
        runfile = "; Information only\n"
    elif has_overrides:
        if not template:
            raise IOError("make_entry: no run script template")
        runfile = make_runscript(entry, template, False)
    else:
        runfile = "execute \"AVS:{}/{}\"".format(query.get_runscript_paths(entry)[0], make_canonical_name(entry))

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
    if options and (options.get("unavailable", False) or options.get("informational", False)):
        note = wrap_note(note if note else entry["title"] + "\n\n" + strings["note"]["unavailable"])
        open(base_path + ".txt", mode="w", encoding="latin-1", errors="replace").write(note)
    elif entry:
        open(base_path + ".txt", mode="w", encoding="latin-1", errors="replace").write(make_note(entry, note))

    # Remember exact menu filenames, including ranked and overridden entries.
    if entry and "id" in entry and ("image" not in entry or is_nsfw(entry)):
        collection.image_entries[os.path.relpath(base_path, avs_path)] = entry["id"]

    # make image
    if entry and is_nsfw(entry):
        install_nsfw_thumbnail(base_path, "medium")
    elif entry and "image" in entry:
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

def metadata_system(entry):
    system = entry["hardware"].replace("/", "·")
    aspect_ratio = None

    if util.parse_int(entry.get("ntsc", 0)) == 1:
        if util.parse_int(entry.get("scale") or 0) == 6:
            system += "·6×NTSC"
            aspect_ratio = "16:9"
        else:
            system += "·5×NTSC"
    elif util.parse_int(entry.get("ntsc", 0)) == 2:
        if util.parse_int(entry.get("scale") or 0) == 6:
            system += "·6×PAL60"
            aspect_ratio = "16:9"
        else:
            system += "·5×PAL60"
    else:
        if util.parse_int(entry.get("scale") or 0) == 6:
            system += "·6×PAL"
            aspect_ratio = "16:9"
        elif util.parse_int(entry.get("scale") or 0) == 5:
            system += "·5×PAL"
        else:
            system += "·4×PAL"

    if util.parse_int(entry.get("lightgun") or 0):
        system += "·Light Gun"
    if util.parse_int(entry.get("gamepad") or 0):
        system += "·Game Pad"
    if aspect_ratio:
        system += " ({})".format(aspect_ratio)

    return system.replace("·", " · ")


def make_note(entry, add_note):
    max_w = AVS_INFO_WIDTH
    system = metadata_system(entry)
    blocks = metadata_blocks(entry, add_note, system)
    wrapped = [(field, metadata_wrap(text)) for field, text in blocks]
    if sum(len(lines) for _, lines in wrapped) > AVS_INFO_HEIGHT:
        print_warning("metadata exceeds {} lines: {}".format(AVS_INFO_HEIGHT, entry.get("id", entry.get("title", ""))))
        # Every semantic field keeps a line, including issues and hardware.
        # Shorten descriptive text first; the audit exposes any such fallback.
        for field in ("note", "hack", "credits", "language", "title", "country_type", "genre_players", "issues", "hardware"):
            for key, lines in wrapped:
                while key == field and len(lines) > 1 and sum(len(value) for _, value in wrapped) > AVS_INFO_HEIGHT:
                    lines.pop()
                    lines[-1] = lines[-1][:max_w - 2].rstrip(" .") + ".."
    if (sum(len(lines) for _, lines in wrapped) <= 6
            and wrapped and wrapped[0][0] == "title" and wrapped[0][1]):
        wrapped[0][1].append("")
        if sum(len(lines) for _, lines in wrapped) < AVS_INFO_HEIGHT:
            wrapped[0][1].insert(0, "")
    return "".join(line.center(max_w).rstrip() + "\n" for _, lines in wrapped for line in lines)


def balanced_wrap(text):
    """Balance centered lines without increasing their greedy wrapping count."""
    greedy = textwrap.wrap(text, AVS_INFO_WIDTH)
    if len(greedy) < 2:
        return greedy
    # Retain textwrap's handling of words longer than the available width.
    words = text.split()
    if any(len(word) > AVS_INFO_WIDTH for word in words):
        return greedy
    count = len(greedy)
    target = (sum(map(len, words)) + len(words) - count) / count
    states = {(0, 0): ((0, 0, 0), [])}
    for line_number in range(count):
        for start in range(len(words)):
            state = states.get((line_number, start))
            if state is None:
                continue
            for end in range(start + 1, len(words) + 1):
                line = " ".join(words[start:end])
                if len(line) > AVS_INFO_WIDTH:
                    break
                remaining = count - line_number - 1
                if len(words) - end < remaining:
                    break
                # Prefer two words per continuation, then intact separators,
                # then similar line lengths. Explicit newlines stay separate.
                score = (state[0][0] + int(line_number > 0 and end - start < 2),
                         state[0][1] + int(words[start] == "·") + int(words[end - 1] == "·"),
                         state[0][2] + (len(line) - target) ** 2)
                key = (line_number + 1, end)
                if key not in states or score < states[key][0]:
                    states[key] = (score, state[1] + [line])
    return states.get((count, len(words)), (None, greedy))[1]


def metadata_wrap(text):
    """Wrap authored prose before centering; output is written as Latin-1."""
    return [line for paragraph in str(text).replace("\\\\n", "\n").replace("\\n", "\n").splitlines()
            for line in balanced_wrap(paragraph.strip())]


def metadata_date(value):
    value = (value or "").strip()
    if re.fullmatch(r"\d{3}[xX]", value):
        return value[:3] + "0s"
    if re.fullmatch(r"\d{2}[xX]{2}", value):
        return ""  # Entirely unknown year, rather than an invented date.
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        from datetime import date
        try:
            day = date.fromisoformat(value)
            months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
            return "{} {} {}".format(day.day, months[day.month - 1], day.year)
        except ValueError:
            pass
    return value


def metadata_blocks(entry, add_note, system):
    """Semantic lines, shared with the metadata audit (before wrapping/clipping)."""
    blocks = []
    def add(field, value):
        if value and str(value).strip():
            blocks.append((field, str(value).strip()))

    add("title", entry.get("title"))
    category = entry.get("category", "").lower()
    seen = set()
    credits = [metadata_date(entry.get("release_date"))]
    for field in (("developer", "publisher") if category == "game" else ("publisher",)):
        names = []
        for name in entry.get(field, "").split(", "):
            name = name.strip()
            if name and name.casefold() not in seen:
                names.append(name)
                seen.add(name.casefold())
        credits.append(", ".join(names))
    add("credits", " · ".join(part for part in credits if part))
    if category == "game":
        players = entry.get("players", "").strip()
        # Legacy/imported numeric counts still render naturally. Rich wording lives in CSV.
        if players.isdigit() and players != "0":
            players += " Player" if players == "1" else " Players"
        if players == "0":
            players = ""
        add("genre_players", " · ".join(part for part in (entry.get("subcategory", "").strip(), players) if part))
        language = entry.get("language", "").strip()
        if language.casefold() != "english":
            languages = query.get_languages(entry)
            if len(metadata_wrap(language)) > 2:
                language = ("English + {} other languages".format(len(languages) - 1)
                            if query.has_english_language(entry)
                            else "{} languages".format(len(languages)))
            add("language", language)
    elif category == "demo":
        add("country_type", " · ".join(part for part in (entry.get("country", "").strip(), entry.get("subcategory", "").strip() or "Demo") if part))
    add("note", add_note if isinstance(add_note, str) and add_note else entry.get("note"))
    add("issues", entry.get("issues"))
    add("hack", entry.get("hack"))
    add("hardware", system)
    return blocks

# -----------------------------------------------------------------------------
# make run scripts

def make_runscripts(collection: EntryCollection, avs_path: str, template=None):
    for _, entry in collection.by_id.items():
        name = make_canonical_name(entry)
        dest_paths = query.get_runscript_paths(entry)
        if dest_paths[0]:
            script = make_runscript(entry, template, False)
            dest = util.path(avs_path, dest_paths[0], name)
            util.make_dir(util.path(avs_path, dest_paths[0]))
            if util.is_file(dest):
                print(" > WARNING: duplicate script at", dest, entry["id"])
            else:
                open(dest, mode="w", encoding="latin-1", errors="replace").write(script)
        if dest_paths[1]:
            script = make_runscript(entry, template, True)
            dest = util.path(avs_path, dest_paths[1], name)
            util.make_dir(util.path(avs_path, dest_paths[1]))
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
        # NTSC pixel proportions (NTSC is the avs-vadjust switch).
        vadjust_ntsc = "NTSC" if util.parse_int(entry.get("ntsc", 0)) == 1 else ""
        if not vadjust_scale: vadjust_scale = 0

        if query.entry_is_notwhdl(entry):
            archive_path = query.get_archive_path(entry)
            if archive_path:
                # New non-WHDLoad imports live in AVSCONTENT first, while some older
                # checked-in titles still only exist in the repo mirror.
                runfile_source_path = util.path(paths.titles(), entry["archive_path"]).replace(".lha", ".run")
                if not util.is_file(runfile_source_path):
                    runfile_source_path = util.path(paths.tracked_titles(), entry["archive_path"]).replace(".lha", ".run")
                if util.is_file(runfile_source_path):
                    script = "avs-notify TITLE=\"{}\"\n".format(entry.get("title", "Unknown"))
                    script += "IF EXISTS ENV:whdlvmode\n  setvmode $whdlvmode\nELSE\n"
                    script += "  set{}\n".format(whd_vmode.lower())
                    script += "  IF NOT EXISTS ENV:disable_vadjust\n    avs-vadjust s={} v={} h={} {}\n  ENDIF\nENDIF\n".format(vadjust_scale, vadjust_vshift, vadjust_hshift, vadjust_ntsc)
                    with open(runfile_source_path, 'r') as f: script += rename_reference(f.read())
                    script += "setvmode $AVSVMode\n"
                    script += "IF NOT EXISTS ENV:whdlvmode\n  IF NOT EXISTS ENV:disable_vadjust\n    avs-vadjust\n  ENDIF\nENDIF\n"
                    script += "avs-notify\n"
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
                    whd_spdly_setup = "" if quiet else "IF NOT EXISTS ENV:whdlspdly\n  echo 200 >ENV:whdlspdly\nENDIF"
                    script = util.apply_template(template, {
                        "TITLE": entry.get("title", "Unknown"),
                        "PATH": whd_entrypath,
                        "SLAVE": query.get_whd_slavename(entry),
                        "CUST_ARGS": whd_cargs,
                        "QUIT_KEY": whd_qtkey,
                        "SPLASH_DELAY": whd_spdly,
                        "SPLASH_DELAY_SETUP": whd_spdly_setup,
                        "CONFIG_DELAY": " ConfigDelay=0" if quiet else "",
                        "VIDEO_MODE": whd_vmode,
                        "VADJUST_SCALE": vadjust_scale,
                        "VADJUST_VSHIFT": vadjust_vshift,
                        "VADJUST_HSHIFT": vadjust_hshift,
                        "VADJUST_NTSC": vadjust_ntsc
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
    d_path = util.path(path, "{}.avs".format(strings["dirs"]["scene"]))
    ne_path = util.path(path, "{}.avs".format(strings["dirs"]["allgames_nonenglish"]))
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
        if "MT-32" in entry.get("hardware", ""):
            c.progress_current += 1
            continue
        letter = entry.get("title_short", "z")[0].upper()
        if not letter.isalpha():
            letter = "#"
        year, year_img = normalize_release_year(entry.get("release_date", ""))

        # add games
        if games and entry.get("category", "").lower() == "game":
            if query.has_english_language(entry):
                start = perf_counter()
                make_entry(c, path, entry, util.path(path, "{}.avs".format(strings["dirs"]["allgames"]), letter + ".avs"))
                add_timing(c, "auto make_entry", perf_counter() - start)
                ensure_image(util.path(path, "{}.avs".format(strings["dirs"]["allgames"]), letter + ".iff"), {"op":"tx", "txt": letter})
                start = perf_counter()
                make_entry(c, path, entry, util.path(path, "{}.avs".format(strings["dirs"]["allgames_year"]), year + ".avs"))
                add_timing(c, "auto make_entry", perf_counter() - start)
                ensure_image(util.path(path, "{}.avs".format(strings["dirs"]["allgames_year"]), year + ".iff"), {"op":"tx", "txt": year_img, "size": 112})
            languages = query.get_languages(entry)
            for language in languages:
                if language.lower() != "english":
                    start = perf_counter()
                    make_entry(c, path, entry, util.path(ne_path, language + ".avs"))
                    add_timing(c, "auto make_entry", perf_counter() - start)
                    flag_path = "flags/{}.png".format(util.country(language).lower())
                    img_ops =  { "ops": { "op": "pi", "path": flag_path }, "size": [320, 128 ], "scale": [1, 1] }
                    ensure_image(util.path(ne_path, language + ".iff"), img_ops)
            if languages and not query.has_english_language(entry) and not entry.get("preferred_version", None):
                start = perf_counter()
                make_entry(c, path, entry, util.path(ne_path, "{}.avs".format(strings["dirs"]["unique_nonenglish"])))
                add_timing(c, "auto make_entry", perf_counter() - start)
                img_ops =  { "ops": { "op": "pi", "path": "flags/eu barcode.png" }, "size": [320, 128 ], "scale": [1, 1] }
                ensure_image(util.path(ne_path, strings["dirs"]["unique_nonenglish"] + ".iff"), img_ops)

        # add demos, disk mags, etc
        def add_demo(entry, sort_group, sort_country):
            if sort_group.startswith("The "):
                sort_group = sort_group[4:]
            sort_group = sort_group[:AVS_LIST_WIDTH]
            group_letter = sort_group[0].upper() if sort_group else None
            if group_letter and not group_letter.isalpha():
                group_letter = "#"
            if entry.get("subcategory", "").lower().startswith("disk mag"):
                start = perf_counter()
                make_entry(c, path, entry, util.path(d_path, "{}.avs".format(strings["dirs"]["diskmags"])))
                add_timing(c, "auto make_entry", perf_counter() - start)
                start = perf_counter()
                mag_path = make_entry(c, path, entry, util.path(d_path, "{}.avs".format(strings["dirs"]["diskmags_date"])))
                add_timing(c, "auto make_entry", perf_counter() - start)
                if mag_path:
                    rank = util.parse_date_int(entry["release_date"], sortable=True)
                    c.path_sort_rank["{}.run".format(mag_path)] = rank if rank else 0
            elif entry.get("subcategory", "").lower().startswith("music disk"):
                start = perf_counter()
                make_entry(c, path, entry, util.path(d_path, "{}.avs".format(strings["dirs"]["musicdisks"]), letter + ".avs"))
                add_timing(c, "auto make_entry", perf_counter() - start)
                ensure_image(util.path(d_path, "{}.avs".format(strings["dirs"]["musicdisks"]), letter + ".iff"), {"op":"tx", "txt": letter})
                start = perf_counter()
                make_entry(c, path, entry, util.path(d_path, "{}.avs".format(strings["dirs"]["musicdisks_year"]), year + ".avs"))
                add_timing(c, "auto make_entry", perf_counter() - start)
                ensure_image(util.path(d_path, "{}.avs".format(strings["dirs"]["musicdisks_year"]), year + ".iff"), {"op":"tx", "txt": year_img, "size": 112})
            elif entry.get("subcategory", "").lower().startswith("slide"):
                start = perf_counter()
                make_entry(c, path, entry, util.path(d_path, "{}.avs".format(strings["dirs"]["slideshows"])))
                add_timing(c, "auto make_entry", perf_counter() - start)
            else:
                if entry.get("subcategory", "").lower().startswith("crack"):
                    start = perf_counter()
                    make_entry(c, path, entry, util.path(d_path, "{}.avs".format(strings["dirs"]["demos_cracktro"])), prefix=sort_group)
                    add_timing(c, "auto make_entry", perf_counter() - start)
                if entry.get("subcategory", "").lower().startswith("intro"):
                    start = perf_counter()
                    make_entry(c, path, entry, util.path(d_path, "{}.avs".format(strings["dirs"]["demos_intro"])))
                    add_timing(c, "auto make_entry", perf_counter() - start)
                group_entry = dict(entry)
                group_entry["disp_name"] = group_entry.get("title")
                start = perf_counter()
                make_entry(c, path, entry, util.path(d_path, "{}.avs".format(strings["dirs"]["demos"]), letter + ".avs"))
                add_timing(c, "auto make_entry", perf_counter() - start)
                ensure_image(util.path(d_path, "{}.avs".format(strings["dirs"]["demos"]), letter + ".iff"), {"op":"tx", "txt": letter})
                if sort_group:
                    start = perf_counter()
                    make_entry(c, path, group_entry, util.path(d_path, "{}.avs".format(strings["dirs"]["demos_group"]), group_letter + ".avs"), prefix=sort_group)
                    add_timing(c, "auto make_entry", perf_counter() - start)
                    ensure_image(util.path(d_path, "{}.avs".format(strings["dirs"]["demos_group"]), group_letter + ".iff"), {"op":"tx", "txt": group_letter})
                start = perf_counter()
                make_entry(c, path, entry, util.path(d_path, "{}.avs".format(strings["dirs"]["demos_year"]), year + ".avs"))
                add_timing(c, "auto make_entry", perf_counter() - start)
                ensure_image(util.path(d_path, "{}.avs".format(strings["dirs"]["demos_year"]), year + ".iff"), {"op":"tx", "txt": year_img, "size": 112})
                if sort_country:
                    start = perf_counter()
                    make_entry(c, path, entry, util.path(d_path, "{}.avs".format(strings["dirs"]["demos_country"]), sort_country + ".avs"))
                    add_timing(c, "auto make_entry", perf_counter() - start)
                    flag_path = "flags/{}.png".format(sort_country.lower())
                    img_ops =  { "ops": { "op": "pi", "path": flag_path }, "size": [320, 128 ], "scale": [1, 1] }
                    ensure_image(util.path(d_path, "{}.avs".format(strings["dirs"]["demos_country"]), sort_country + ".iff"), img_ops)

        if demos and entry.get("category", "").lower() == "demo":
            groups = query.get_publishers(entry)
            # Missing group credits must not hide titles from alphabet/year lists.
            for sort_group in groups or [""]:
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
        if util.is_dir(util.path(path, "{}.avs".format(strings["dirs"][dir]))):
            open(util.path(path, "{}.txt".format(strings["dirs"][dir])), mode="w", encoding="latin-1", errors="replace").write(wrap_note(strings["desc"][dir]))
            img_src = util.path("top", strings["images"][dir])
            if util.is_file("{}{}".format(compositor.IMG_SRC_BASE, img_src)):
                make_image(util.path(path, "{}.iff".format(strings["dirs"][dir])), {"ops":{"op":"pi", "path":img_src}, "size":[320,128], "scale":[1,1]})

    for dir in [
        "demos", "demos_country", "demos_group", "demos_year", "demos_cracktro", "demos_intro",
        "diskmags", "diskmags_date", "musicdisks", "musicdisks_year", "slideshows"
    ]:
        if util.is_dir(util.path(d_path, "{}.avs".format(strings["dirs"][dir]))):
            open(util.path(d_path, "{}.txt".format(strings["dirs"][dir])), mode="w", encoding="latin-1", errors="replace").write(wrap_note(strings["desc"][dir]))

    for dir in ["unique_nonenglish"]:
        if util.is_dir(util.path(ne_path, "{}.avs".format(strings["dirs"][dir]))):
            open(util.path(ne_path, "{}.txt".format(strings["dirs"][dir])), mode="w", encoding="latin-1", errors="replace").write(wrap_note(strings["desc"][dir]))

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("not runnable")
    sys.exit(1)


def make_hires_artwork(avs_path, hires_path, collection):
    """Copy pre-rendered category/navigation artwork without image conversion."""

    title_images = {
        relpath + suffix
        for relpath in collection.image_entries
        for suffix in [".iff", "-QR.iff"] + [f"-{i}.iff" for i in range(1, 10)]
    }
    copied = 0
    for source in Path(avs_path).rglob("*.iff"):
        relpath = source.relative_to(avs_path)
        if str(relpath) in title_images or source.name.startswith("skin-") or source.stem.lower().endswith("-qr"):
            continue
        override = Path(util.path("data", "img_highres")) / relpath
        if not override.is_file():
            raise FileNotFoundError(
                f"Missing static hi-res artwork: {override}. "
                "Add the pre-rendered 360x288 IFF using at most 240 colors before building."
            )
        destination = Path(hires_path) / relpath
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(override, destination)
        copied += 1
    print(f" > HiRes: copied {copied} static category/navigation images")


def report_missing_launcher_images(avs_path, hires_path, collection, medium_files=None, hires_files=None):
    """Report the actual built menu thumbnails, including restored cache trees."""
    for label, root, inventory in (("Med-res", avs_path, medium_files), ("Hi-res", hires_path, hires_files)):
        if inventory is not None:
            available = {name for name in inventory if name.endswith('.iff')}
        else:
            available = set()
            for directory, _, filenames in os.walk(root):
                relative = Path(directory).relative_to(root)
                available.update((relative / name).as_posix() for name in filenames if name.endswith('.iff'))
        missing = {}
        for path, entry_id in collection.image_entries.items():
            if any(path + suffix in available for suffix in ['.iff'] + [f'-{i}.iff' for i in range(1, 10)]):
                continue
            missing.setdefault(entry_id, []).append(path)
        count = sum(len(paths) for paths in missing.values())
        if not missing:
            print(f" > {label}: All entries have screenshots")
            continue
        print(f" > {label}: {count} menu entries have no screenshot ({len(missing)} titles)")
        for entry_id, paths in sorted(missing.items()):
            title = collection.by_id.get(entry_id, {}).get('title') or Path(paths[0]).name
            print(f"   - {title} ({entry_id})")
            for path in sorted(paths):
                print(f"     {path}")


def make_hires_tree(avs_path, hires_path, collection):
    """Clone the completed launcher and replace its configuration and title images."""
    util.rm_path(hires_path)
    ignore_empty = shutil.ignore_patterns("skin-empty*.iff")
    util.copytree(avs_path, hires_path, ignore=ignore_empty)
    make_hires_artwork(avs_path, hires_path, collection)
    util.copytree(util.path("data", "avs-highres"), hires_path)
    shutil.copyfile(util.path(hires_path, "AVS.conf"), util.path(hires_path, "AVS.conf.base"))
    image_root = Path(util.path("data", "img_highres"))
    images = {}
    for source in sorted(image_root.glob("*.iff")) + sorted((image_root / "qr").glob("*.iff")):
        images.setdefault(source.stem, source)
    # Informational menu items (such as About) also have launcher-local QR art.
    # Their old folder artwork is removed below along with other medium assets.
    for source in sorted(Path("data/avs-highres").glob("*-qr.iff")):
        images.setdefault(source.stem, source)
    for relpath, entry_id in collection.image_entries.items():
        base = Path(hires_path) / relpath
        # Remove medium-resolution slides and QR images from title entries.
        for suffix in [".iff", "-QR.iff"] + [f"-{i}.iff" for i in range(1, 10)]:
            image = Path(str(base) + suffix)
            if image.is_file():
                image.unlink()
        if is_nsfw(collection.by_id.get(entry_id, {})):
            install_nsfw_thumbnail(base, "hires")
            continue
        found = False
        for key, suffix in [(entry_id, ".iff"), (entry_id + "-qr", "-QR.iff")] + [
            (entry_id + f"-{i}", f"-{i}.iff") for i in range(1, 10)
        ]:
            if key in images:
                shutil.copyfile(images[key], str(base) + suffix)
                found = found or suffix != "-QR.iff"
        if found and not Path(str(base) + ".iff").is_file():
            for index in [3, 2, 1, 4, 5, 6, 7, 8, 9]:
                slide = Path(str(base) + f"-{index}.iff")
                if slide.is_file():
                    shutil.copyfile(slide, str(base) + ".iff")
                    break
