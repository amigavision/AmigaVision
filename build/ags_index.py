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
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from lhafile import LhaFile, is_lhafile
from lhafile.lhafile import BadLhafile
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
    ignored_dirs = {"retired", "manual-downloads", "imported"}
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


SIMULMONDO_EPISODE_TITLES = {
    "Diabolik": {
        "01": "Diabolik 01: Inafferrabile Criminale",
        "02": "Diabolik 02: La Gemma Di Salomone",
        "03": "Diabolik 03: La Fuga",
        "04": "Diabolik 04: Trappola D'Acciaio",
        "05": "Diabolik 05: Ore Pericolose",
        "06": "Diabolik 06: La Notte Della Paura",
        "07": "Diabolik 07: 4 Diamanti Unici",
        "08": "Diabolik 08: Un Piano Perfetto",
        "09": "Diabolik 09: A Caro Prezzo",
        "10": "Diabolik 10: All'Ultimo Sangue",
        "11": "Diabolik 11: Inganno Fatale",
        "12": "Diabolik 12: Terrore A Teatro",
    },
    "DylanDog": {
        "01": "Dylan Dog 01: La Regina Delle Tenebre",
        "02": "Dylan Dog 02: Ritorno Al Crepuscolo",
        "03": "Dylan Dog 03: Storia Di Nessuno",
        "04": "Dylan Dog 04: Ombre",
        "05": "Dylan Dog 05: La Mummia",
        "06": "Dylan Dog 06: Maelstrom",
        "07": "Dylan Dog 07: Gente Che Scompare",
        "08": "Dylan Dog 08: La Clessidra Di Pietra",
        "09": "Dylan Dog 09: Il Male",
        "10": "Dylan Dog 10: I Vampiri",
        "11": "Dylan Dog 11: Il Marchio Rosso",
        "12": "Dylan Dog 12: Il Lungo Addio",
        "13": "Dylan Dog 13: I Killers Venuti Dal Buio",
        "14": "Dylan Dog 14: Il Bosco Degli Assassini",
        "15": "Dylan Dog 15: Inferni",
        "16": "Dylan Dog 16: Fantasmi",
        "17": "Dylan Dog 17: Il Cimitero Dimenticato",
    },
}

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
    return "English"

def load_csv_rows_by_id(csv_path="data/db/titles.csv"):
    rows = {}
    with open(csv_path, "r") as f:
        for row in csv.DictReader(f, delimiter=";"):
            rows[row["id"]] = row
    return rows

def needs_remote_game_enrichment(existing_row):
    if existing_row is None:
        return True
    hol_id = (existing_row.get("hol_id") or "").strip()
    lemon_id = (existing_row.get("lemon_id") or "").strip()
    has_known_external_id = hol_id not in ("", "0") or lemon_id not in ("", "0")
    if has_known_external_id:
        return not (existing_row.get("release_date") or "").strip()
    fields = (
        "title",
        "subcategory",
        "hol_id",
        "lemon_id",
        "language",
        "developer",
        "publisher",
        "players",
        "hardware",
        "release_date",
    )
    return any(not existing_row.get(field) for field in fields)

def csv_enrichment_fields(archive_path, existing_row=None):
    title = humanize_archive_name(archive_path)
    entry = {
        "title": title,
        "title_short": infer_title_short(title),
        **csv_category_fields(archive_path),
        "hardware": infer_hardware_from_archive(archive_path),
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
        entry.update(fallback_game_metadata([title], existing_row=existing_row))
        entry["title_short"] = infer_title_short(entry.get("title", title))
    return entry

def humanize_archive_name(archive_path):
    stem = Path(archive_path).name[:-4]
    name = stem.split("_v", 1)[0]
    match = re.fullmatch(r"(Diabolik|DylanDog)(\d{2})(?:It)?", name)
    if match:
        series, episode = match.groups()
        canonical_title = SIMULMONDO_EPISODE_TITLES.get(series, {}).get(episode)
        if canonical_title:
            return canonical_title
    return humanize_name(name)

def infer_title_short(title, max_length=28):
    return util.infer_title_short_from_title(title, max_length=max_length)

def infer_aga_flag(archive_path):
    archive_upper = Path(archive_path).name.upper()
    return "1" if ("_AGA" in archive_upper or "CD32" in archive_upper) else ""

def infer_hardware_from_archive(archive_path):
    path = Path(archive_path)
    archive_upper = path.name.upper()
    rel_parts_upper = [part.upper() for part in path.parts]
    if "ARCADIA" in archive_upper or "ARCADIA" in rel_parts_upper:
        return "Arcadia"
    if "_MT32" in archive_upper or "_MT32" in rel_parts_upper:
        return "OCS/MT-32"
    if "CD32" in archive_upper:
        return "CD32"
    if "CDTV" in archive_upper:
        return "CDTV"
    is_aga = "_AGA" in archive_upper
    is_cd = "_CD" in archive_upper or archive_upper.endswith("CD.LHA")
    if is_aga and "060" in archive_upper:
        return "AGA/060"
    if is_aga and "030" in archive_upper:
        return "AGA/030"
    if is_aga and is_cd:
        return "AGA/CD"
    if is_aga:
        return "AGA"
    if is_cd:
        return "OCS/CD"
    return "OCS"

def normalized_title(value):
    return "".join(ch.lower() for ch in value if ch.isalnum())

def compact_labels(labels, max_items=None):
    compacted = []
    seen = set()
    for label in labels:
        label = (label or "").strip()
        if not label:
            continue
        key = label.lower()
        if key in seen:
            continue
        seen.add(key)
        compacted.append(label)
    if max_items is not None and len(compacted) > max_items:
        return []
    return compacted

def normalize_wikidata_date(value):
    if not value:
        return ""

    precision = None
    if isinstance(value, dict):
        precision = value.get("precision")
        value = value.get("time", "")

    text = str(value).strip()
    match = re.match(r"^[+-]?(\d{4})-(\d{2})-(\d{2})", text)
    if not match:
        return ""

    year, month, day = match.groups()
    if precision is not None:
        try:
            precision = int(precision)
        except Exception:
            precision = None
    if precision is not None and precision <= 9:
        return year
    if month == "01" and day == "01":
        return year
    return f"{year}-{month}-{day}"

def wikidata_api(params):
    url = "https://www.wikidata.org/w/api.php?" + urlencode(params)
    request = Request(url, headers={
        "User-Agent": "AmigaVision/1.0 (local build tooling)",
        "Accept": "application/json",
    })
    with urlopen(request, timeout=15) as response:
        return json.load(response)

def wikidata_sparql(query):
    request = Request(
        "https://query.wikidata.org/sparql?" + urlencode({"format": "json", "query": query}),
        headers={
            "User-Agent": "AmigaVision/1.0 (local build tooling)",
            "Accept": "application/sparql-results+json, application/json",
        },
    )
    with urlopen(request, timeout=20) as response:
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

def wikidata_entity_id_from_uri(uri):
    if not uri:
        return ""
    value = str(uri).rstrip("/")
    return value.rsplit("/", 1)[-1]


def fetch_wikidata_entities(candidate_ids):
    candidate_ids = [candidate_id for candidate_id in dict.fromkeys(candidate_ids) if candidate_id]
    if not candidate_ids:
        return {}
    try:
        return wikidata_api({
            "action": "wbgetentities",
            "format": "json",
            "languages": "en",
            "props": "labels|claims",
            "ids": "|".join(candidate_ids),
        }).get("entities", {})
    except Exception:
        return {}


def score_wikidata_entity(entity, search_title):
    label = entity_label(entity)
    hol_id = wikidata_claim_value(entity, "P4671")
    lemon_id = wikidata_claim_value(entity, "P4846")
    if not hol_id and not lemon_id:
        return None
    score = 0
    normalized_label = normalized_title(label)
    target = normalized_title(search_title)
    if normalized_label == target:
        score += 100
    elif target and (target in normalized_label or normalized_label in target):
        score += 50
    score += int(bool(hol_id)) + int(bool(lemon_id))
    return score


def build_game_metadata_from_entity(entity, search_title):
    try:
        language_ids = wikidata_item_ids(entity, "P407")
        developer_ids = wikidata_item_ids(entity, "P178")
        publisher_ids = wikidata_item_ids(entity, "P123")
        country_ids = wikidata_item_ids(entity, "P495")
        genre_ids = wikidata_item_ids(entity, "P136")
        related_entities = wikidata_labels_for_ids(language_ids + developer_ids + publisher_ids + country_ids + genre_ids, include_claims=True)

        if not country_ids and developer_ids:
            developer_country_ids = []
            for developer_id in developer_ids:
                developer_entity = related_entities.get(developer_id, {})
                developer_country_ids.extend(wikidata_item_ids(developer_entity, "P495"))
                developer_country_ids.extend(wikidata_item_ids(developer_entity, "P17"))
            country_ids = [id for id in dict.fromkeys(developer_country_ids) if id]
            if country_ids:
                related_entities.update(wikidata_labels_for_ids(country_ids))

        languages = compact_labels([entity_label(related_entities.get(id, {})) for id in language_ids])
        developers = compact_labels([entity_label(related_entities.get(id, {})) for id in developer_ids], max_items=4)
        publishers = compact_labels([entity_label(related_entities.get(id, {})) for id in publisher_ids], max_items=4)
        countries = compact_labels([entity_label(related_entities.get(id, {})) for id in country_ids], max_items=4)
        genres = compact_labels([entity_label(related_entities.get(id, {})) for id in genre_ids])

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
            "subcategory": map_wikidata_genres_to_subcategory(genres),
            "release_date": normalize_wikidata_date(wikidata_claim_value(entity, "P577")),
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
            "subcategory": "",
            "release_date": normalize_wikidata_date(wikidata_claim_value(entity, "P577")),
            "language": "",
            "developer": "",
            "publisher": "",
            "players": "",
            "country": "",
            "hol_id": str(wikidata_claim_value(entity, "P4671") or ""),
            "lemon_id": str(wikidata_claim_value(entity, "P4846") or ""),
        }


def relaxed_search_titles(title):
    variants = []
    seen = set()

    def add(candidate):
        candidate = re.sub(r"\s+", " ", (candidate or "").strip())
        if not candidate or candidate in seen:
            return
        seen.add(candidate)
        variants.append(candidate)

    add(title)
    words = re.findall(r"[A-Za-z0-9']+", title or "")
    stopwords = {"the", "and", "of", "a", "an", "demo", "edition", "version", "remastered", "shareware", "aga", "cd32", "cdtv", "amiga"}
    significant = [word for word in words if len(word) >= 4 and word.lower() not in stopwords]
    if significant:
        add(" ".join(significant))
        longest = sorted(significant, key=lambda word: (-len(word), words.index(word)))[:3]
        ordered = [word for word in words if word in longest]
        add(" ".join(ordered))
        if len(ordered) >= 2:
            add(" ".join(ordered[:2]))
    return variants


def enrich_game_metadata_with_queries(search_titles, existing_row=None):
    for search_title in search_titles:
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
            continue
        candidate_ids = [item["id"] for item in search_data.get("search", [])]
        entities = fetch_wikidata_entities(candidate_ids)
        best = None
        for entity_id in candidate_ids:
            entity = entities.get(entity_id, {})
            score = score_wikidata_entity(entity, search_title)
            if score is None:
                continue
            if best is None or score > best[0]:
                best = (score, entity)
        if best is not None:
            return build_game_metadata_from_entity(best[1], search_title)
    fallback_title = search_titles[0] if search_titles else ""
    return {"title": fallback_title, "title_short": infer_title_short(fallback_title), "release_date": "", "language": "", "developer": "", "publisher": "", "players": "", "country": "", "hol_id": "", "lemon_id": ""}

def map_wikidata_genres_to_subcategory(genres):
    normalized = [genre.strip().lower() for genre in genres if genre and genre.strip()]
    mapping = {
        "platform game": "Platform",
        "puzzle video game": "Puzzle",
        "puzzle game": "Puzzle",
        "graphic adventure game": "Adventure",
        "adventure game": "Adventure",
        "interactive fiction": "Adventure",
        "point-and-click adventure game": "Adventure",
        "action-adventure game": "Action Adventure",
        "action game": "Action",
        "strategy video game": "Strategy",
        "real-time strategy": "Strategy",
        "god game": "Strategy",
        "turn-based strategy video game": "Strategy",
        "tactical role-playing game": "Strategy",
        "role-playing video game": "RPG",
        "action role-playing game": "Action RPG",
        "dungeon crawl": "RPG",
        "racing video game": "Racing",
        "arcade racing game": "Racing",
        "simulation video game": "Simulation",
        "business simulation game": "Simulation",
        "construction and management simulation": "Simulation",
        "flight simulator": "Simulation",
        "space flight simulator game": "Simulation",
        "sports video game": "Sports",
        "association football video game": "Sports",
        "baseball video game": "Sports",
        "basketball video game": "Sports",
        "boxing video game": "Sports",
        "bowling video game": "Sports",
        "cricket video game": "Sports",
        "golf video game": "Sports",
        "ice hockey video game": "Sports",
        "tennis video game": "Sports",
        "volleyball video game": "Sports",
        "wrestling video game": "Sports",
        "shoot 'em up": "Shoot'em Up",
        "horizontally scrolling shooter": "Shoot'em Up",
        "vertically scrolling shooter": "Shoot'em Up",
        "run and gun": "Action",
        "beat 'em up": "Action",
        "fighting game": "Action",
        "board game": "Board Game",
        "chess": "Board Game",
    }
    for genre in normalized:
        if genre in mapping:
            return mapping[genre]
    return ""

def enrich_game_metadata_by_existing_ids(existing_row):
    hol_id = (existing_row or {}).get("hol_id", "").strip()
    lemon_id = (existing_row or {}).get("lemon_id", "").strip()
    if not hol_id and not lemon_id:
        return None
    conditions = []
    if hol_id:
        conditions.append(f'?item wdt:P4671 "{hol_id}" .')
    if lemon_id:
        conditions.append(f'?item wdt:P4846 "{lemon_id}" .')
    query = """
SELECT ?item WHERE {{
  {conditions}
}}
LIMIT 5
""".format(conditions="\n  ".join(conditions))
    try:
        data = wikidata_sparql(query)
    except Exception:
        return None
    bindings = data.get("results", {}).get("bindings", [])
    candidate_ids = [wikidata_entity_id_from_uri(binding.get("item", {}).get("value", "")) for binding in bindings]
    entities = fetch_wikidata_entities(candidate_ids)
    for candidate_id in candidate_ids:
        entity = entities.get(candidate_id, {})
        if not entity:
            continue
        metadata = build_game_metadata_from_entity(entity, (existing_row or {}).get("title", "") or "")
        metadata["hol_id"] = metadata.get("hol_id") or hol_id
        metadata["lemon_id"] = metadata.get("lemon_id") or lemon_id
        return metadata
    return None


def fallback_game_metadata(search_titles, existing_row=None):
    fallback_title = search_titles[0] if search_titles else ""
    return {
        "title": fallback_title,
        "title_short": infer_title_short(fallback_title),
        "release_date": "",
        "language": (existing_row or {}).get("language", "") or "",
        "developer": (existing_row or {}).get("developer", "") or "",
        "publisher": (existing_row or {}).get("publisher", "") or "",
        "players": (existing_row or {}).get("players", "") or "",
        "country": (existing_row or {}).get("country", "") or "",
        "subcategory": (existing_row or {}).get("subcategory", "") or "",
        "hol_id": (existing_row or {}).get("hol_id", "") or "",
        "lemon_id": (existing_row or {}).get("lemon_id", "") or "",
    }


def enrich_game_metadata(archive_path, existing_row=None, relaxed=False, allow_wikidata_fallback=False):
    search_title = humanize_archive_name(archive_path)
    exact_match = enrich_game_metadata_by_existing_ids(existing_row)
    if exact_match:
        return exact_match
    search_titles = [search_title]
    if relaxed:
        search_titles = relaxed_search_titles(search_title)
    if not allow_wikidata_fallback:
        return fallback_game_metadata(search_titles, existing_row=existing_row)
    return enrich_game_metadata_with_queries(search_titles, existing_row=existing_row)


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

def index_whdload_archives(basedir, verbose=False):
    basedir += os.sep
    print("Enumerating archives...", flush=True)
    count = 0
    d = {}
    for r, _, f in os.walk(basedir):
        for file in f:
            if file.endswith(".lha"):
                count += 1
                path = util.path(r, file)
                if verbose and count % 100 == 0:
                    rel_path = path.split(basedir, 1)[1]
                    print("Enumerating archives... [{}] {}".format(count, rel_path), flush=True)
                if is_ignored_archive_path(basedir, path):
                    continue
                if not is_lhafile(path):
                    print("{} is not a valid lha file".format(path), flush=True)
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
    errors = []
    for r, _, f in os.walk(titles_dir):
        for file in f:
            path = util.path(r, file)
            if is_ignored_archive_path(titles_dir, path):
                continue
            contents, error = make_manifest(titles_dir, manifests_dir, path, only_missing)
            if error:
                errors.append(error)
                continue
            if contents:
                count += 1
                if count % 100 == 0: print(".", end="", flush=True)
    print("\n", flush=True)
    for error in errors:
        print(error, flush=True)
    return errors

def make_manifest(titles_dir, manifests_dir, path, only_missing=False):
    yaml_path = manifest_path_for_archive(titles_dir, manifests_dir, path)
    contents = None
    if only_missing and util.is_file(yaml_path):
        return None, None
    if path.endswith(".lha") and is_lhafile(path):
        try:
            contents = make_lha_manifest(path)
        except (BadLhafile, RuntimeError) as exc:
            return None, "lha manifest failed: {} ({})".format(path, exc)
    if contents:
        os.makedirs(os.path.dirname(yaml_path), exist_ok=True)
        with open(yaml_path, 'w') as f:
            yaml.round_trip_dump(contents, f, explicit_start=True, version=(1, 2))
    return contents, None

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
                    try:
                        hasher.update(arc.read(mf))
                    except BadLhafile as exc:
                        return "• Failed to read file '{}' in '{}' ({})".format(mf, lha_path, exc)
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

def report_missing_required_metadata(csv_rows_by_id, ids=None):
    required_fields = (
        ("category", "Category"),
        ("publisher", "Publisher"),
        ("release_date", "Year"),
        ("language", "Language"),
    )
    missing_by_field = {field: [] for field, _ in required_fields}
    rows = csv_rows_by_id.values() if ids is None else [csv_rows_by_id[id] for id in ids if id in csv_rows_by_id]
    for row in rows:
        if not row.get("archive_path"):
            continue
        for field, _ in required_fields:
            if not row.get(field):
                missing_by_field[field].append(row["id"])

    printed = False
    for field, label in required_fields:
        ids_for_field = missing_by_field[field]
        if not ids_for_field:
            continue
        if not printed:
            print("Missing required metadata:")
            printed = True
        print("• {} ({}):".format(label, len(ids_for_field)))
        for id in ids_for_field:
            print(id)
        print()
    return printed

def missing_language_ids(csv_rows_by_id, ids=None):
    rows = csv_rows_by_id.values() if ids is None else [csv_rows_by_id[id] for id in ids if id in csv_rows_by_id]
    missing = []
    for row in rows:
        if not row.get("archive_path"):
            continue
        if not row.get("language"):
            missing.append(row["id"])
    return sorted(set(missing))

def print_missing_language_report(csv_rows_by_id):
    missing_ids = missing_language_ids(csv_rows_by_id)
    if not missing_ids:
        return 0

    print("Language cleanup:")
    print("• Archive-backed titles default to English unless the archive name contains an explicit language suffix such as DE, FR, or IT.")
    print("• Rows still needing manual review:")
    for row_id in missing_ids:
        print(row_id)
    print()
    return len(missing_ids)

def build_db_row_maps(db):
    exact_rows_by_id = {}
    variant_rows_by_base_id = defaultdict(list)
    for row in db.cursor().execute("SELECT * FROM titles"):
        exact_rows_by_id[row["id"]] = row
        parts = row["id"].split("--")
        if len(parts) > 3:
            variant_rows_by_base_id["--".join(parts[:-1])].append(row)
    return exact_rows_by_id, variant_rows_by_base_id

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
    parser.add_argument("--ingest", dest="ingest", action="store_true", default=False, help="index archives, append missing CSV rows, and write CSV")
    parser.add_argument("--audit", dest="audit", action="store_true", default=False, help="report missing archives, images, and manifests")
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", default=False, help="verbose output")

    try:
        paths.verify()
        args = parser.parse_args()
        sync_csv = args.append_missing_csv or args.ingest

        if args.make_csv:
            if args.verbose:
                print("Writing data/db/titles.csv from SQLite...")
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
        csv_rows_by_id = load_csv_rows_by_id() if sync_csv else {}

        if args.make_manifests:
            manifest_errors = make_manifests(titles_dir, manifests_dir, only_missing=args.only_missing)
            return 1 if manifest_errors else 0

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
        missing_db_archive_refs = 0
        removed_db_archive_refs = 0
        prune_missing_archive_refs = args.apply and sync_csv and not args.ingest
        for r in db.cursor().execute("SELECT * FROM titles"):
            if r["archive_path"] and not util.is_file(util.path(titles_dir, r["archive_path"])):
                missing_db_archive_refs += 1
                label = "• Archive reference removed from DB:" if prune_missing_archive_refs else "• Archive reference missing from titles tree:"
                print(label, r["id"])
                print(r["archive_path"])
                if prune_missing_archive_refs:
                    db.cursor().execute("UPDATE titles SET archive_path=NULL,slave_path=NULL,slave_version=NULL WHERE id=?;", (r["id"],))
                    removed_db_archive_refs += 1
                print()

        # enumerate whdl archives, correlate with db
        archives = list(index_whdload_archives(titles_dir, verbose=args.verbose).items())
        total_archives = len(archives)
        exact_rows_by_id, variant_rows_by_base_id = build_db_row_maps(db)
        csv_enrichment_entries = [] if sync_csv else None
        if args.verbose:
            print("Correlating archives with title database...")
        for archive_progress, (_, arc) in enumerate(archives, start=1):
            rows = []
            exact_row = exact_rows_by_id.get(arc["id"])
            if exact_row:
                rows.append(exact_row)
            rows.extend(variant_rows_by_base_id.get(arc["id"], []))
            if args.verbose and (archive_progress == 1 or archive_progress % 250 == 0 or archive_progress == total_archives):
                print("Correlating archives... {}/{}".format(archive_progress, total_archives), flush=True)
            existing_csv_row = csv_rows_by_id.get(arc["id"])
            should_enrich_game = (
                sync_csv
                and Path(arc["archive_path"]).parts[0] == "game"
                and needs_remote_game_enrichment(existing_csv_row)
            )
            enrichment_fields = None
            if sync_csv:
                enrichment_fields = csv_enrichment_fields(
                    arc["archive_path"],
                    existing_csv_row,
                )
            if not rows:
                print("• No DB entry:", arc["archive_path"])
                print(arc["id"])
                print()
                if sync_csv:
                    entry = {
                        "id": arc["id"],
                        "archive_path": arc["archive_path"],
                        "slave_path": arc["slave_path"],
                        "slave_version": arc["slave_version"],
                        **enrichment_fields,
                    }
                    csv_enrichment_entries.append(entry)
                continue
            for row in rows:
                if sync_csv:
                    csv_enrichment_entries.append({
                        "id": row["id"],
                        "archive_path": arc["archive_path"],
                        "slave_path": arc["slave_path"],
                        "slave_version": arc["slave_version"],
                        **enrichment_fields,
                    })
                if not row["archive_path"]:
                    db.cursor().execute("UPDATE titles SET archive_path=?,slave_path=?,slave_version=? WHERE id=?;",
                                        (arc["archive_path"], arc["slave_path"], arc["slave_version"], row["id"]))
                    print("archive added: " + arc["archive_path"] + " -> " +row["id"])
                    print()

        if sync_csv:
            db.commit()
            util.write_csv()
            report_path = Path("data/db/index-add-missing-report.html").resolve()
            added, updated, report_entries = util.append_missing_title_rows(csv_enrichment_entries)
            skipped = sum(1 for entry in report_entries if entry.get("status") == "skipped")
            if added or updated or skipped:
                if added:
                    print("• Appended {} missing title ID(s) to data/db/titles.csv".format(added))
                if updated:
                    print("• Filled inferred title/title_short/category/subcategory/AGA/language/developer/publisher/players/HOL/Lemon fields for {} existing row(s)".format(updated))
                if skipped:
                    print("• Skipped {} new game row(s) missing required metadata; review the ID verification report".format(skipped))
                util.write_id_verification_report(report_entries, report_path=str(report_path))
                print("• Wrote ID verification report to {}".format(report_path))
                print()
            else:
                print("No missing title IDs or inferred CSV fields needed to be updated in data/db/titles.csv")
                print()
            if args.ingest:
                refreshed_csv_rows = load_csv_rows_by_id()
                changed_ids = [entry["id"] for entry in report_entries]
                if not report_missing_required_metadata(refreshed_csv_rows, ids=changed_ids):
                    print("No missing required metadata in changed archive-backed CSV rows")
                    print()
                missing_language_count = print_missing_language_report(refreshed_csv_rows)
                if not missing_language_count:
                    print("Language cleanup:")
                    print("• No archive-backed rows are missing Language metadata")
                    print()
            elif report_path.is_file():
                subprocess.run(["open", str(report_path)], check=False)
        else:
            if removed_db_archive_refs:
                print("• Removed {} stale archive reference(s) from the DB; run 'make csv' to persist those changes to data/db/titles.csv".format(removed_db_archive_refs))
                print()
            elif missing_db_archive_refs:
                print("• Found {} missing archive reference(s); DB rows were left unchanged".format(missing_db_archive_refs))
                print("• Run 'make prune-missing-archives' to clear archive/slave references for those rows")
                print()

        # list missing content
        if args.audit:
            missing_archives = []
            missing_images = []
            missing_manifests = []
            title_rows = list(exact_rows_by_id.values())
            total_title_rows = len(title_rows)
            print("Checking for missing archives, images, and manifests...")
            for title_progress, r in enumerate(title_rows, start=1):
                if args.verbose and (title_progress == 1 or title_progress % 250 == 0 or title_progress == total_title_rows):
                    print("Checking indexed titles... {}/{}".format(title_progress, total_title_rows), flush=True)
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
