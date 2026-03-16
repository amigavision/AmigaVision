#!/usr/bin/env python3

# AGSImager: Indexer

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

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

def is_ignored_archive_path(titles_dir, archive_path):
    rel_parts = Path(os.path.relpath(archive_path, titles_dir)).parts
    ignored_dirs = {"retired", "manual-downloads", "mega-downloads", "imported"}
    return any(part in ignored_dirs for part in rel_parts)

def csv_category_fields(archive_path):
    category_dir = Path(archive_path).parts[0]
    if category_dir == "game":
        return {"category": "Game", "subcategory": ""}
    if category_dir == "demo":
        return {"category": "Demo", "subcategory": "Demo"}
    if category_dir == "mags":
        return {"category": "Demo", "subcategory": "Disk Magazine"}
    return {"category": "", "subcategory": ""}

def humanize_name(value):
    value = value.replace("_", " ").replace("&", " & ")
    value = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", value)
    value = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    value = re.sub(r"(?<=[A-Za-z])(?=[0-9])", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()

def infer_demo_publisher(archive_path):
    parts = Path(archive_path).parts
    if not parts or parts[0] != "demo" or (len(parts) > 1 and parts[1].startswith("_")):
        return ""
    stem = Path(archive_path).stem
    if "_v" not in stem:
        return ""
    _, versioned = stem.split("_v", 1)
    tokens = versioned.split("_")[1:]
    if not tokens:
        return ""
    stop_tokens = {
        "AGA", "CD32", "CDTV", "FAST", "NTSC", "PAL", "ECS", "OCS",
        "DECRUNCHED", "CRUNCHED", "FIX", "FILES", "IMAGE", "NOINTRO",
    }
    ignore_tokens = {
        "COMPLETEEDITION", "SPECIALEDITION", "DELUXE", "FINAL", "INTRO",
        "INVITATION", "REMASTERED", "REMASTER", "RELOADED",
    }
    publisher_tokens = []
    for token in tokens:
        if token.upper() in ignore_tokens:
            continue
        if token.upper() in stop_tokens:
            break
        publisher_tokens.append(token)
    if not publisher_tokens:
        return ""
    return humanize_name(" ".join(publisher_tokens))

def infer_language_from_archive(archive_path):
    parts = Path(archive_path).parts
    if not parts:
        return ""
    if parts[0] == "demo":
        return "English"
    stem_tokens = Path(archive_path).stem.split("_")
    language_map = {
        "DE": "German",
        "ES": "Spanish",
        "FR": "French",
        "IT": "Italian",
        "PL": "Polish",
        "GR": "Greek",
        "DK": "Danish",
        "SE": "Swedish",
        "NL": "Dutch",
        "PT": "Portuguese",
        "RU": "Russian",
        "FI": "Finnish",
        "NO": "Norwegian",
        "HU": "Hungarian",
        "CZ": "Czech",
        "CS": "Czech",
        "SK": "Slovak",
        "HR": "Croatian",
        "SR": "Serbian",
        "RO": "Romanian",
    }
    for token in reversed(stem_tokens[1:]):
        if token.isdigit() or token.startswith("v"):
            continue
        mapped = language_map.get(token.upper())
        if mapped:
            return mapped
    return ""

def load_csv_rows_by_id(csv_path="data/db/titles.csv"):
    rows = {}
    with open(csv_path, "r") as f:
        for row in csv.DictReader(f, delimiter=";"):
            rows[row["id"]] = row
    return rows

def needs_remote_game_enrichment(existing_row):
    if existing_row is None:
        return True
    fields = ("title", "hol_id", "lemon_id", "language", "developer", "publisher", "players")
    return any(not existing_row.get(field) for field in fields)

def csv_enrichment_fields(archive_path, existing_row=None):
    title = humanize_archive_name(archive_path)
    entry = {
        "title": title,
        "title_short": infer_title_short(title),
        **csv_category_fields(archive_path),
        "aga": infer_aga_flag(archive_path),
        "language": infer_language_from_archive(archive_path),
        "developer": "",
        "publisher": "",
        "players": "",
        "country": "",
        "hol_id": "",
        "lemon_id": "",
    }
    if entry["category"] == "Demo":
        entry["publisher"] = infer_demo_publisher(archive_path)
    if entry["category"] == "Game" and needs_remote_game_enrichment(existing_row):
        entry.update(enrich_game_metadata(archive_path))
        entry["title_short"] = infer_title_short(entry.get("title", title))
    return entry

def humanize_archive_name(archive_path):
    stem = Path(archive_path).name[:-4]
    name = stem.split("_v", 1)[0]
    return humanize_name(name)

def infer_title_short(title, max_length=28):
    return (title or "")[:max_length].strip()

def infer_aga_flag(archive_path):
    return "1" if "_AGA" in Path(archive_path).name.upper() else ""

def normalized_title(value):
    return "".join(ch.lower() for ch in value if ch.isalnum())

def wikidata_api(params):
    url = "https://www.wikidata.org/w/api.php?" + urlencode(params)
    request = Request(url, headers={
        "User-Agent": "AmigaVision/1.0 (local build tooling)",
        "Accept": "application/json",
    })
    with urlopen(request, timeout=15) as response:
        return json.load(response)

def wikidata_claim_value(entity, prop):
    claims = entity.get("claims", {}).get(prop, [])
    if not claims:
        return ""
    try:
        return claims[0]["mainsnak"]["datavalue"]["value"]
    except Exception:
        return ""

def wikidata_item_ids(entity, prop):
    ids = []
    for claim in entity.get("claims", {}).get(prop, []):
        try:
            value = claim["mainsnak"]["datavalue"]["value"]
            if isinstance(value, dict) and value.get("id"):
                ids.append(value["id"])
        except Exception:
            continue
    return ids

def wikidata_quantities(entity, prop):
    values = []
    for claim in entity.get("claims", {}).get(prop, []):
        try:
            value = claim["mainsnak"]["datavalue"]["value"]
            amount = value.get("amount", "")
            if amount:
                values.append(int(float(amount)))
        except Exception:
            continue
    return values

def wikidata_labels_for_ids(ids, include_claims=False):
    ids = [id for id in dict.fromkeys(ids) if id]
    if not ids:
        return {}
    props = "labels|claims" if include_claims else "labels"
    return wikidata_api({
        "action": "wbgetentities",
        "format": "json",
        "languages": "en",
        "props": props,
        "ids": "|".join(ids),
    }).get("entities", {})

def entity_label(entity):
    return entity.get("labels", {}).get("en", {}).get("value", "")

def enrich_game_metadata(archive_path):
    search_title = humanize_archive_name(archive_path)
    try:
        search_data = wikidata_api({
            "action": "wbsearchentities",
            "format": "json",
            "language": "en",
            "type": "item",
            "limit": 10,
            "search": search_title,
        })
    except Exception:
        return {"title": search_title, "title_short": infer_title_short(search_title), "language": "", "developer": "", "publisher": "", "players": "", "country": "", "hol_id": "", "lemon_id": ""}
    candidate_ids = [item["id"] for item in search_data.get("search", [])]
    if not candidate_ids:
        return {"title": search_title, "title_short": infer_title_short(search_title), "language": "", "developer": "", "publisher": "", "players": "", "country": "", "hol_id": "", "lemon_id": ""}

    try:
        entities = wikidata_api({
            "action": "wbgetentities",
            "format": "json",
            "languages": "en",
            "props": "labels|claims",
            "ids": "|".join(candidate_ids),
        }).get("entities", {})
    except Exception:
        return {"title": search_title, "title_short": infer_title_short(search_title), "language": "", "developer": "", "publisher": "", "players": "", "country": "", "hol_id": "", "lemon_id": ""}

    best = None
    target = normalized_title(search_title)
    for entity_id in candidate_ids:
        entity = entities.get(entity_id, {})
        label = entity_label(entity)
        hol_id = wikidata_claim_value(entity, "P4671")
        lemon_id = wikidata_claim_value(entity, "P4846")
        if not hol_id and not lemon_id:
            continue
        score = 0
        normalized_label = normalized_title(label)
        if normalized_label == target:
            score += 100
        elif target and (target in normalized_label or normalized_label in target):
            score += 50
        score += int(bool(hol_id)) + int(bool(lemon_id))
        if best is None or score > best[0]:
            best = (score, entity)

    if best is None:
        return {"title": search_title, "title_short": infer_title_short(search_title), "language": "", "developer": "", "publisher": "", "players": "", "country": "", "hol_id": "", "lemon_id": ""}

    entity = best[1]
    try:
        language_ids = wikidata_item_ids(entity, "P407")
        developer_ids = wikidata_item_ids(entity, "P178")
        publisher_ids = wikidata_item_ids(entity, "P123")
        country_ids = wikidata_item_ids(entity, "P495")
        related_entities = wikidata_labels_for_ids(language_ids + developer_ids + publisher_ids + country_ids, include_claims=True)

        if not country_ids and developer_ids:
            developer_country_ids = []
            for developer_id in developer_ids:
                developer_entity = related_entities.get(developer_id, {})
                developer_country_ids.extend(wikidata_item_ids(developer_entity, "P495"))
                developer_country_ids.extend(wikidata_item_ids(developer_entity, "P17"))
            country_ids = [id for id in dict.fromkeys(developer_country_ids) if id]
            if country_ids:
                related_entities.update(wikidata_labels_for_ids(country_ids))

        languages = [entity_label(related_entities.get(id, {})) for id in language_ids]
        developers = [entity_label(related_entities.get(id, {})) for id in developer_ids]
        publishers = [entity_label(related_entities.get(id, {})) for id in publisher_ids]
        countries = [entity_label(related_entities.get(id, {})) for id in country_ids]

        min_players = wikidata_quantities(entity, "P1872")
        max_players = wikidata_quantities(entity, "P1873")
        players = ""
        if min_players and max_players:
            players = str(min_players[0]) if min_players[0] == max_players[0] else f"{min_players[0]}-{max_players[0]}"
        elif min_players:
            players = str(min_players[0])
        elif max_players:
            players = str(max_players[0])

        return {
            "title": entity_label(entity) or search_title,
            "title_short": infer_title_short(entity_label(entity) or search_title),
            "language": ", ".join([label for label in languages if label]),
            "developer": ", ".join([label for label in developers if label]),
            "publisher": ", ".join([label for label in publishers if label]),
            "players": players,
            "country": ", ".join([label for label in countries if label]),
            "hol_id": str(wikidata_claim_value(entity, "P4671") or ""),
            "lemon_id": str(wikidata_claim_value(entity, "P4846") or ""),
        }
    except Exception:
        return {
            "title": entity_label(entity) or search_title,
            "title_short": infer_title_short(entity_label(entity) or search_title),
            "language": "",
            "developer": "",
            "publisher": "",
            "players": "",
            "country": "",
            "hol_id": str(wikidata_claim_value(entity, "P4671") or ""),
            "lemon_id": str(wikidata_claim_value(entity, "P4846") or ""),
        }

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
                if is_ignored_archive_path(basedir, path):
                    continue
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
            path = util.path(r, file)
            if is_ignored_archive_path(titles_dir, path):
                continue
            if make_manifest(titles_dir, manifests_dir, path, only_missing):
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

def finish_progress_line(progress_active):
    if progress_active:
        print()
        print()
    return False

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
    parser.add_argument("--append-missing-csv", dest="append_missing_csv", action="store_true", default=False, help="append missing title IDs to data/db/titles.csv")
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
        csv_rows_by_id = load_csv_rows_by_id() if args.append_missing_csv else {}

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
        removed_db_archive_refs = 0
        for r in db.cursor().execute("SELECT * FROM titles"):
            if r["archive_path"] and not util.is_file(util.path(titles_dir, r["archive_path"])):
                print("• Archive reference removed from DB:", r["id"])
                print(r["archive_path"])
                db.cursor().execute("UPDATE titles SET archive_path=NULL,slave_path=NULL,slave_version=NULL WHERE id=?;", (r["id"],))
                removed_db_archive_refs += 1
                print()

        # enumerate whdl archives, correlate with db
        archives = list(index_whdload_archives(titles_dir).items())
        total_game_enrichment = sum(
            1
            for _, arc in archives
            if args.append_missing_csv
            and Path(arc["archive_path"]).parts[0] == "game"
            and needs_remote_game_enrichment(csv_rows_by_id.get(arc["id"]))
        )
        csv_enrichment_entries = []
        printed_wikidata_status = False
        printed_wikidata_progress = False
        game_enrichment_progress = 0
        for _, arc in archives:
            rows = db.cursor().execute("SELECT * FROM titles WHERE (id = ?) OR (id LIKE ?);", (arc["id"], arc["id"] + '--%',)).fetchall()
            existing_csv_row = csv_rows_by_id.get(arc["id"])
            should_enrich_game = (
                args.append_missing_csv
                and Path(arc["archive_path"]).parts[0] == "game"
                and needs_remote_game_enrichment(existing_csv_row)
            )
            if should_enrich_game and not printed_wikidata_status:
                print("Querying Wikidata for game metadata...")
                printed_wikidata_status = True
            enrichment_fields = None
            if should_enrich_game:
                game_enrichment_progress += 1
                if game_enrichment_progress == 1 or game_enrichment_progress % 25 == 0 or game_enrichment_progress == total_game_enrichment:
                    print("\rWikidata: {}/{}".format(game_enrichment_progress, total_game_enrichment), end="", flush=True)
                    printed_wikidata_progress = True
                enrichment_fields = csv_enrichment_fields(arc["archive_path"], existing_csv_row)
            else:
                enrichment_fields = csv_enrichment_fields(arc["archive_path"], existing_csv_row)
            if not rows:
                printed_wikidata_progress = finish_progress_line(printed_wikidata_progress)
                print("• No DB entry:", arc["archive_path"])
                print(arc["id"])
                print()
                entry = {
                    "id": arc["id"],
                    **enrichment_fields,
                }
                csv_enrichment_entries.append(entry)
                continue
            for row in rows:
                csv_enrichment_entries.append({
                    "id": row["id"],
                    **enrichment_fields,
                })
                if not row["archive_path"]:
                    printed_wikidata_progress = finish_progress_line(printed_wikidata_progress)
                    db.cursor().execute("UPDATE titles SET archive_path=?,slave_path=?,slave_version=? WHERE id=?;",
                                        (arc["archive_path"], arc["slave_path"], arc["slave_version"], row["id"]))
                    print("archive added: " + arc["archive_path"] + " -> " +row["id"])
                    print()

        if printed_wikidata_progress:
            print()

        if args.append_missing_csv:
            util.write_csv()
            report_path = Path("data/db/index-add-missing-report.html").resolve()
            added, updated, report_entries = util.append_missing_title_rows(csv_enrichment_entries)
            if added or updated:
                if added:
                    print("• Appended {} missing title ID(s) to data/db/titles.csv".format(added))
                if updated:
                    print("• Filled inferred title/title_short/category/subcategory/AGA/language/developer/publisher/players/country/HOL/Lemon fields for {} existing row(s)".format(updated))
                util.write_id_verification_report(report_entries, report_path=str(report_path))
                print("• Wrote ID verification report to {}".format(report_path))
                print()
            else:
                print("No missing title IDs or inferred CSV fields needed to be updated in data/db/titles.csv")
                print()
            if report_path.is_file():
                subprocess.run(["open", str(report_path)], check=False)
        else:
            missing_ids = [entry["id"] for entry in csv_enrichment_entries if not db.cursor().execute("SELECT 1 FROM titles WHERE id=?;", (entry["id"],)).fetchone()]
            if missing_ids:
                print("• Found {} missing title ID(s); run 'make index-add-missing' to append them to data/db/titles.csv".format(len(set(missing_ids))))
                print()
            if removed_db_archive_refs:
                print("• Removed {} stale archive reference(s) from the DB; run 'make csv' to persist those changes to data/db/titles.csv".format(removed_db_archive_refs))
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
