#!/usr/bin/env python3

import argparse
import csv
import json
import os
import re
import shutil
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from lhafile import LhaFile

import ags_util as util


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTENT_ROOT = Path(os.getenv("AGSCONTENT", "~/Developer/AmigaVision-Content")).expanduser()
DEFAULT_SOURCE_ROOT = DEFAULT_CONTENT_ROOT / "titles" / "manual-downloads"
DEFAULT_TITLES_DIR = DEFAULT_CONTENT_ROOT / "titles"
DEFAULT_CSV_PATH = ROOT / "data" / "db" / "titles.csv"
DEFAULT_REPORT_PATH = ROOT / "data" / "cache" / "demo-notwhdl-import-report.json"
DEFAULT_METADATA_CACHE_PATH = ROOT / "data" / "cache" / "demo-notwhdl-metadata-cache.json"
DEFAULT_ARCHIVE_CACHE_PATH = ROOT / "data" / "cache" / "demo-notwhdl-archive-cache.json"

USER_AGENT = "Mozilla/5.0"
DOC_EXTENSIONS = {
    ".txt", ".nfo", ".diz", ".readme", ".md", ".org", ".pdf", ".guide", ".info",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".iff", ".tga",
    ".adf", ".dms", ".zip", ".lha", ".lzx",
    ".dat", ".bin", ".res", ".expr", ".eph", ".cgx", ".tndo", ".zx0",
}
SKIP_NAMES = {
    "readme", "readme.txt", "file_id.diz", "scene.org.txt", "title", "text",
    "data", "bonus",
}
FOLDER_DEFAULTS = {
    "AGA Demos": {"hardware": "AGA", "aga": "1", "subcategory": "Demo"},
    "AGA 64K": {"hardware": "AGA", "aga": "1", "subcategory": "Intro 64K"},
    "OCS Demos": {"hardware": "OCS", "aga": "", "subcategory": "Demo"},
    "OCS 64K": {"hardware": "OCS", "aga": "", "subcategory": "Intro 64K"},
}
RUN_OVERRIDES = {
    "FocusDesign-1992-060": "mainpart.exe",
    "PlanetJazz-MagnumAI": "magnumai.exe",
    "SpaceBalls-NorwegianKindness": "RenGodhetFraSpaceballs.exe",
    "Spreadpoint-PlusEqualsPlus": "spreadpoint-plusequalsplus",
    "TheBlackLotus-Final": "Start",
}
NOTE_OVERRIDES = {
    "Spaceballs-GoonRoyale": "Requires 060 CPU",
}
TITLE_OVERRIDES = {
    "SpaceBalls-NorwegianKindness": "Norwegian Kindness",
}
DEVELOPER_OVERRIDES = {
    "SpaceBalls": "Spaceballs",
    "TheBlackLotus": "The Black Lotus",
    "FocusDesign": "Focus Design",
    "DemostueAllstars": "Demostue Allstars",
    "AttentionWhore": "Attention Whore",
    "PlanetJazz": "Planet Jazz",
}
POUET_RESULT_RE = re.compile(r'href="(?:https?://www\.pouet\.net)?/prod\.php\?which=(?P<id>\d+)"[^>]*>(?P<title>[^<]+)</a>', re.IGNORECASE)
POUET_GROUP_RE = re.compile(r'<span class="prod\">.*?</span>\s*by\s*(?P<group>.*?)\s*<', re.IGNORECASE | re.DOTALL)
POUET_DATE_RE = re.compile(r'<td class="r">date</td>\s*<td class="v">(?P<value>[^<]+)</td>', re.IGNORECASE)
POUET_PLATFORM_RE = re.compile(r'<td class="r">platform</td>\s*<td class="v">(?P<value>[^<]+)</td>', re.IGNORECASE)
POUET_TYPE_RE = re.compile(r'<td class="r">type</td>\s*<td class="v">(?P<value>[^<]+)</td>', re.IGNORECASE)
DEMOZOO_TITLE_RE = re.compile(r'<h1[^>]*>\s*(?P<title>.*?)\s*</h1>', re.IGNORECASE | re.DOTALL)
DEMOZOO_RELEASE_RE = re.compile(r'Released\s+(?P<date>\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{4}|\d{4})', re.IGNORECASE)
DEMOZOO_PLATFORM_RE = re.compile(r'<li[^>]*class="platform"[^>]*>\s*(?P<value>.*?)\s*</li>', re.IGNORECASE | re.DOTALL)
DEMOZOO_TYPE_RE = re.compile(r' - (?P<value>Demo|Invitation|Musicdisk|Slideshow|Cracktro|64K Intro|40k Intro|4K Intro|8K Intro|16K Intro|32K Intro)', re.IGNORECASE)
DEMOZOO_POUET_RE = re.compile(r'https?://(?:www\.)?pouet\.net/prod\.php\?which=(?P<id>\d+)', re.IGNORECASE)


@dataclass
class Candidate:
    archive_path: Path
    archive_name: str
    parent_name: str
    run_command: str | None
    adf_only: bool
    status: str
    reasons: list
    entry: dict
    existing_row: dict | None
    metadata_source: str


def parse_args():
    parser = argparse.ArgumentParser(description="Import repacked non-WHDLoad demo archives from manual-downloads.")
    parser.add_argument("--source-root", default=str(DEFAULT_SOURCE_ROOT))
    parser.add_argument("--titles-dir", default=str(DEFAULT_TITLES_DIR))
    parser.add_argument("--csv", default=str(DEFAULT_CSV_PATH))
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--metadata-cache", default=str(DEFAULT_METADATA_CACHE_PATH))
    parser.add_argument("--archive-cache", default=str(DEFAULT_ARCHIVE_CACHE_PATH))
    parser.add_argument("--apply", action="store_true", default=False, help="Copy archives into demo-notwhdl, write .run files, and update titles.csv")
    parser.add_argument("--skip-online", action="store_true", default=False, help="Do not query Pouet or Demozoo")
    return parser.parse_args()


def slug_words(value: str) -> list[str]:
    pieces = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    pieces = pieces.replace("_", " ").replace("+", " + ").replace("&", " & ")
    return [part for part in re.split(r"[\s\-]+", pieces) if part]


def humanize_slug(value: str) -> str:
    if value in DEVELOPER_OVERRIDES:
        return DEVELOPER_OVERRIDES[value]
    words = slug_words(value)
    normalized = []
    for word in words:
        if word in {"+", "&"}:
            normalized.append(word)
        elif word.isupper() and len(word) > 1:
            normalized.append(word)
        elif re.fullmatch(r"\d+[A-Za-z]+", word):
            normalized.append(word)
        else:
            normalized.append(word[0].upper() + word[1:])
    return " ".join(normalized).replace(" + ", ", ").strip()


def normalized_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def normalize_title_tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (value or "").lower())


def title_match_score(query: str, candidate: str) -> float:
    query_tokens = set(normalize_title_tokens(query))
    candidate_tokens = set(normalize_title_tokens(candidate))
    if not query_tokens or not candidate_tokens:
        return 0.0
    overlap = len(query_tokens & candidate_tokens)
    if not overlap:
        return 0.0
    return overlap / max(len(query_tokens), len(candidate_tokens))


def pick_best_title_match(query: str, candidates: list[dict], minimum_score: float = 0.6):
    best = None
    best_score = 0.0
    for candidate in candidates:
        score = title_match_score(query, candidate.get("title", ""))
        if score > best_score:
            best = candidate
            best_score = score
    if best and best_score >= minimum_score:
        return best
    return None


def fetch_url(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=8) as response:
        return response.read().decode("utf-8", errors="ignore")


def load_csv_rows(csv_path: Path):
    with csv_path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def load_json(path: Path, default):
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_existing_indexes(rows):
    by_archive = {}
    by_normalized_title = {}
    for row in rows:
        archive_path = (row.get("archive_path") or "").strip()
        if archive_path:
            by_archive[Path(archive_path).name] = row
        title_key = normalized_key(row.get("title", ""))
        if title_key:
            by_normalized_title.setdefault(title_key, []).append(row)
    return by_archive, by_normalized_title


def list_manual_archives(source_root: Path):
    for folder_name in FOLDER_DEFAULTS:
        folder = source_root / folder_name
        if not folder.is_dir():
            continue
        for archive_path in sorted(folder.glob("*.lha")):
            yield archive_path


def archive_top_level_entries(archive_path: Path):
    names = LhaFile(str(archive_path)).namelist()
    return [Path(name) for name in names if len(Path(name).parts) == 2]


def analyze_archive(archive_path: Path):
    if archive_path.stem in RUN_OVERRIDES:
        top_level = archive_top_level_entries(archive_path)
        adf_only = determine_adf_only(top_level)
        return {
            "run_command": RUN_OVERRIDES[archive_path.stem],
            "reasons": ["manual override"],
            "adf_only": adf_only,
        }

    candidates = []
    top_level = archive_top_level_entries(archive_path)
    for path in top_level:
        name = path.name
        lower_name = name.lower()
        suffix = path.suffix.lower()
        if suffix in DOC_EXTENSIONS:
            continue
        if lower_name in SKIP_NAMES:
            continue
        candidates.append(name)

    if len(candidates) == 1:
        return {
            "run_command": candidates[0],
            "reasons": ["single executable candidate"],
            "adf_only": determine_adf_only(top_level),
        }

    reasons = []
    if not candidates:
        reasons.append("no obvious top-level executable")
        return {
            "run_command": None,
            "reasons": reasons,
            "adf_only": determine_adf_only(top_level),
        }

    exe_candidates = [name for name in candidates if name.lower().endswith(".exe")]
    if len(exe_candidates) == 1:
        reasons.append("selected lone .exe from multiple candidates")
        return {
            "run_command": exe_candidates[0],
            "reasons": reasons,
            "adf_only": determine_adf_only(top_level),
        }

    plain_candidates = [name for name in candidates if "-uncrunched" not in name.lower()]
    if len(plain_candidates) == 1:
        reasons.append("selected non-uncrunched variant")
        return {
            "run_command": plain_candidates[0],
            "reasons": reasons,
            "adf_only": determine_adf_only(top_level),
        }

    reasons.append("multiple executable candidates")
    return {
        "run_command": None,
        "reasons": reasons,
        "adf_only": determine_adf_only(top_level),
    }


def determine_adf_only(top_level):
    adf_entries = [path for path in top_level if path.suffix.lower() in {".adf", ".dms"}]
    non_doc_entries = []
    for path in top_level:
        name = path.name.lower()
        if path.suffix.lower() in DOC_EXTENSIONS or name in SKIP_NAMES:
            continue
        non_doc_entries.append(path)
    return bool(adf_entries) and not non_doc_entries


def archive_cache_key(archive_path: Path):
    stat = archive_path.stat()
    return f"{archive_path}:{stat.st_size}:{int(stat.st_mtime)}"


def analyze_archive_cached(archive_path: Path, archive_cache: dict):
    key = archive_cache_key(archive_path)
    cached = archive_cache.get(key)
    if cached:
        return cached
    result = analyze_archive(archive_path)
    archive_cache[key] = result
    return result


def split_group_and_title(stem: str):
    if "-" not in stem:
        return "", stem
    group, title = stem.split("-", 1)
    return group, title


def metadata_from_folder(parent_name: str, archive_name: str):
    defaults = FOLDER_DEFAULTS[parent_name]
    group_slug, title_slug = split_group_and_title(archive_name)
    title_slug = re.sub(r"-060$", "", title_slug)
    title = TITLE_OVERRIDES.get(archive_name, humanize_slug(title_slug))
    developer = humanize_slug(group_slug) if group_slug else ""
    hardware = defaults["hardware"]
    if archive_name.endswith("-060"):
        hardware = "AGA/060"
    return {
        "title": title,
        "title_short": title,
        "category": "Demo",
        "subcategory": defaults["subcategory"],
        "hardware": hardware,
        "aga": defaults["aga"],
        "ntsc": "0",
        "language": "English",
        "players": "",
        "developer": "",
        "note": NOTE_OVERRIDES.get(archive_name, ""),
        "archive_path": f"demo-notwhdl/{archive_name}.lha",
        "slave_path": "",
        "slave_version": "",
        "country": "",
        "publisher": developer,
        "release_date": "",
        "demozoo_id": "",
        "pouet_id": "",
    }


def pouet_search(title: str, developer: str):
    query = " ".join(part for part in (title, developer) if part).strip()
    if not query:
        return None
    url = "https://www.pouet.net/search.php?what={}&type=prod".format(urllib.parse.quote(query))
    html = fetch_url(url)
    for match in POUET_RESULT_RE.finditer(html):
        return {"pouet_id": match.group("id"), "title": match.group("title").strip()}
    return None


def pouet_details(pouet_id: str):
    url = f"https://www.pouet.net/prod.php?which={pouet_id}"
    html = fetch_url(url)
    result = {"pouet_id": pouet_id}
    date_match = POUET_DATE_RE.search(html)
    if date_match:
        result["release_date"] = normalize_year_or_date(date_match.group("value"))
    platform_match = POUET_PLATFORM_RE.search(html)
    if platform_match:
        platform = clean_html(platform_match.group("value"))
        if "AGA" in platform:
            result["hardware"] = "AGA"
            result["aga"] = "1"
        elif "OCS" in platform or "ECS" in platform or "Amiga" in platform:
            result["hardware"] = "OCS"
    type_match = POUET_TYPE_RE.search(html)
    if type_match:
        result["subcategory"] = normalize_subcategory(clean_html(type_match.group("value")))
    group_match = POUET_GROUP_RE.search(html)
    if group_match:
        result["publisher"] = clean_html(group_match.group("group")).replace(" / ", ", ")
    return result


def demozoo_search(title: str, developer: str):
    search_queries = []
    if title and developer:
        search_queries.append(f"{title} {developer}")
    if title:
        search_queries.append(title)
    if developer and developer.lower() not in title.lower():
        search_queries.append(f"{developer} {title}")
    if not search_queries:
        return None
    for query in search_queries:
        url = f"https://demozoo.org/search/live/?q={urllib.parse.quote(query)}&category=production"
        try:
            payload = fetch_url(url)
        except Exception:
            continue
        try:
            results = json.loads(payload)
        except json.JSONDecodeError:
            continue
        candidates = []
        for item in results:
            if item.get("type") != "production":
                continue
            url_value = item.get("url", "")
            match = re.search(r"/productions/(?P<id>\d+)/", url_value)
            if not match:
                continue
            candidates.append({
                "demozoo_id": match.group("id"),
                "title": item.get("value", ""),
            })
        best = pick_best_title_match(title, candidates)
        if best:
            return {"demozoo_id": best["demozoo_id"]}
    return None


def demozoo_details(demozoo_id: str):
    url = f"https://demozoo.org/productions/{demozoo_id}/"
    html = fetch_url(url)
    result = {"demozoo_id": demozoo_id}
    title_match = DEMOZOO_TITLE_RE.search(html)
    if title_match:
        result["title"] = clean_html(title_match.group("title"))
    release_match = DEMOZOO_RELEASE_RE.search(html)
    if release_match:
        result["release_date"] = normalize_year_or_date(release_match.group("date"))
    platform_match = DEMOZOO_PLATFORM_RE.search(html)
    if platform_match:
        platform = clean_html(platform_match.group("value"))
        if "AGA" in platform:
            result["hardware"] = "AGA"
            result["aga"] = "1"
        elif "OCS" in platform or "ECS" in platform:
            result["hardware"] = "OCS"
    type_match = DEMOZOO_TYPE_RE.search(html)
    if type_match:
        result["subcategory"] = normalize_subcategory(clean_html(type_match.group("value")))
    pouet_match = DEMOZOO_POUET_RE.search(html)
    if pouet_match:
        result["pouet_id"] = pouet_match.group("id")
    return result


def normalize_year_or_date(value: str) -> str:
    value = clean_html(value).strip()
    if not value:
        return ""

    iso_match = re.search(r"(?P<year>(?:19|20)\d{2})-(?P<month>\d{2})-(?P<day>\d{2})", value)
    if iso_match:
        return f"{iso_match.group('year')}-{iso_match.group('month')}-{iso_match.group('day')}"

    month_map = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12",
    }
    full_match = re.search(r"(?P<day>\d{1,2})\s+(?P<month>[A-Za-z]+)\s+(?P<year>(?:19|20)\d{2})", value)
    if full_match:
        month = month_map.get(full_match.group("month").lower())
        if month:
            return f"{full_match.group('year')}-{month}-{int(full_match.group('day')):02d}"

    month_year_match = re.search(r"(?P<month>[A-Za-z]+)\s+(?P<year>(?:19|20)\d{2})", value)
    if month_year_match:
        month = month_map.get(month_year_match.group("month").lower())
        if month:
            return f"{month_year_match.group('year')}-{month}"

    year_match = re.search(r"(19|20)\d{2}", value)
    if year_match:
        return year_match.group(0)
    return value


def normalize_subcategory(value: str) -> str:
    lowered = value.lower().replace("k ", "K ").replace("40k", "40K").replace("64k", "64K")
    if "crack" in lowered:
        return "Crack Intro"
    if "music" in lowered:
        return "Music Disk"
    if "slide" in lowered:
        return "Slide Show"
    if "64k" in lowered:
        return "Intro 64K"
    if "40k" in lowered:
        return "Intro 40K"
    if "8k" in lowered:
        return "Intro 8K"
    if "4k" in lowered:
        return "Intro 4K"
    if "invit" in lowered:
        return "Demo"
    if "demo" in lowered:
        return "Demo"
    return value


def clean_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("&amp;", "&")
    value = value.replace("&quot;", '"')
    value = value.replace("&#39;", "'")
    return re.sub(r"\s+", " ", value).strip()


def merge_if_blank(target: dict, source: dict):
    for key, value in source.items():
        if value and not target.get(key):
            target[key] = value


def finalize_candidate_status(candidate: Candidate):
    status = "ready"
    reasons = [
        reason for reason in candidate.reasons
        if not reason.startswith("missing release date metadata")
    ]
    if candidate.adf_only:
        status = "deferred-adf"
        if "archive is disk-image-only for now" not in reasons:
            reasons.append("archive is disk-image-only for now")
    elif candidate.existing_row:
        status = "already-indexed"
        if "archive basename already present in titles.csv" not in reasons:
            reasons.append("archive basename already present in titles.csv")
    elif candidate.run_command is None:
        status = "manual-review"
    elif not candidate.entry.get("release_date"):
        status = "manual-review"
        reasons.append("missing release date metadata")
    candidate.status = status
    candidate.reasons = reasons
    return candidate


def build_candidate(archive_path: Path, existing_by_archive: dict, archive_cache: dict):
    archive_name = archive_path.stem
    parent_name = archive_path.parent.name
    defaults = metadata_from_folder(parent_name, archive_name)
    archive_analysis = analyze_archive_cached(archive_path, archive_cache)
    run_command = archive_analysis["run_command"]
    reasons = list(archive_analysis["reasons"])
    existing_row = existing_by_archive.get(archive_path.name)
    metadata_source = "filename"

    if existing_row:
        merge_if_blank(defaults, {
            "title": existing_row.get("title", ""),
            "title_short": existing_row.get("title_short", ""),
            "release_date": existing_row.get("release_date", ""),
            "country": existing_row.get("country", ""),
            "language": existing_row.get("language", ""),
            "subcategory": existing_row.get("subcategory", ""),
            "hardware": existing_row.get("hardware", ""),
            "aga": existing_row.get("aga", ""),
            "note": existing_row.get("note", ""),
            "demozoo_id": existing_row.get("demozoo_id", ""),
            "pouet_id": existing_row.get("pouet_id", ""),
        })
        metadata_source = "existing-row"

    entry = {
        "id": f"demo-notwhdl--{archive_name.lower()}",
        "_force_fields": ["developer", "publisher", "players"],
        **defaults,
    }
    candidate = Candidate(
        archive_path=archive_path,
        archive_name=archive_name,
        parent_name=parent_name,
        run_command=run_command,
        adf_only=archive_analysis["adf_only"],
        status="pending",
        reasons=reasons,
        entry=entry,
        existing_row=existing_row,
        metadata_source=metadata_source,
    )
    return finalize_candidate_status(candidate)


def should_enrich_online(candidate: Candidate):
    if candidate.status == "deferred-adf":
        return False
    if candidate.entry.get("release_date") and candidate.entry.get("demozoo_id") and candidate.entry.get("pouet_id"):
        return False
    return True


def enrich_online(candidate: Candidate):
    entry_updates = {}
    metadata_source = candidate.metadata_source
    reasons = []
    direct_demozoo_id = (candidate.entry.get("demozoo_id") or "").strip()
    direct_pouet_id = (candidate.entry.get("pouet_id") or "").strip()

    if direct_demozoo_id:
        try:
            merge_if_blank(entry_updates, demozoo_details(direct_demozoo_id))
            metadata_source = "demozoo"
        except Exception as exc:
            reasons.append(f"demozoo lookup failed: {exc}")

    if direct_pouet_id and (not entry_updates.get("release_date") or not entry_updates.get("publisher")):
        try:
            merge_if_blank(entry_updates, pouet_details(direct_pouet_id))
            if metadata_source == "filename":
                metadata_source = "pouet"
        except Exception as exc:
            reasons.append(f"pouet lookup failed: {exc}")

    try:
        demozoo_match = demozoo_search(candidate.entry["title"], candidate.entry["developer"])
        if demozoo_match and not entry_updates.get("demozoo_id"):
            merge_if_blank(entry_updates, demozoo_match)
            merge_if_blank(entry_updates, demozoo_details(demozoo_match["demozoo_id"]))
            metadata_source = "demozoo"
    except Exception as exc:
        reasons.append(f"demozoo lookup failed: {exc}")

    resolved_pouet_id = (entry_updates.get("pouet_id") or direct_pouet_id or "").strip()
    if resolved_pouet_id and (not entry_updates.get("publisher") or not entry_updates.get("release_date") or not entry_updates.get("subcategory")):
        try:
            merge_if_blank(entry_updates, pouet_details(resolved_pouet_id))
            if metadata_source == "filename":
                metadata_source = "pouet"
        except Exception as exc:
            reasons.append(f"pouet lookup failed: {exc}")

    # Fall back to direct Pouet search only when Demozoo did not find a hit.
    if not entry_updates.get("release_date") and not entry_updates.get("demozoo_id"):
        try:
            pouet_match = pouet_search(candidate.entry["title"], candidate.entry["developer"])
            if pouet_match:
                merge_if_blank(entry_updates, pouet_match)
                merge_if_blank(entry_updates, pouet_details(pouet_match["pouet_id"]))
                if metadata_source == "filename":
                    metadata_source = "pouet"
        except Exception as exc:
            reasons.append(f"pouet lookup failed: {exc}")

    return {
        "archive_name": candidate.archive_name,
        "entry_updates": entry_updates,
        "metadata_source": metadata_source,
        "reasons": reasons,
    }


def enrich_candidates_online(candidates: list[Candidate], metadata_cache: dict):
    pending = [candidate for candidate in candidates if should_enrich_online(candidate)]

    def apply_cached(candidate: Candidate, cached: dict):
        merge_if_blank(candidate.entry, cached.get("entry_updates", {}))
        candidate.metadata_source = cached.get("metadata_source", candidate.metadata_source)
        candidate.reasons.extend(cached.get("reasons", []))
        return finalize_candidate_status(candidate)

    uncached = []
    for candidate in pending:
        cached = metadata_cache.get(candidate.archive_name)
        if cached:
            apply_cached(candidate, cached)
        else:
            uncached.append(candidate)

    if not uncached:
        return candidates, metadata_cache

    max_workers = min(6, max(1, len(uncached)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(enrich_online, candidate): candidate for candidate in uncached}
        for future in as_completed(futures):
            candidate = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                candidate.reasons.append(f"online lookup failed: {exc}")
                finalize_candidate_status(candidate)
                continue
            merge_if_blank(candidate.entry, result["entry_updates"])
            candidate.metadata_source = result["metadata_source"]
            candidate.reasons.extend(result["reasons"])
            finalize_candidate_status(candidate)
            metadata_cache[candidate.archive_name] = result

    return candidates, metadata_cache


def write_report(candidates: list[Candidate], report_path: Path):
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = []
    for candidate in candidates:
        payload.append({
            "archive": str(candidate.archive_path),
            "status": candidate.status,
            "metadata_source": candidate.metadata_source,
            "run_command": candidate.run_command,
            "reasons": candidate.reasons,
            "entry": candidate.entry,
            "existing_id": candidate.existing_row.get("id") if candidate.existing_row else "",
        })
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_run_file(run_path: Path, archive_name: str, run_command: str):
    run_path.parent.mkdir(parents=True, exist_ok=True)
    run_path.write_text(f"ags-cd N/{archive_name}\n{run_command} >NIL:\n", encoding="utf-8")


def apply_candidates(candidates: list[Candidate], titles_dir: Path, csv_path: Path):
    demo_dir = titles_dir / "demo-notwhdl"
    demo_dir.mkdir(parents=True, exist_ok=True)
    csv_entries = []
    for candidate in candidates:
        dest_archive_name = candidate.archive_path.name
        if candidate.existing_row and candidate.existing_row.get("archive_path"):
            dest_archive_name = Path(candidate.existing_row["archive_path"]).name
        dest_archive = demo_dir / dest_archive_name

        should_sync_existing = (
            candidate.status == "already-indexed"
            and candidate.existing_row
            and candidate.existing_row.get("archive_path")
            and Path(candidate.existing_row["archive_path"]).parts[0] == "demo-notwhdl"
            and (
                not dest_archive.is_file()
                or not dest_archive.with_suffix(".run").is_file()
            )
        )

        if candidate.status == "ready" or should_sync_existing:
            shutil.copy2(candidate.archive_path, dest_archive)
            write_run_file(dest_archive.with_suffix(".run"), candidate.archive_name, candidate.run_command)

        if candidate.status == "ready" or candidate.existing_row:
            csv_entries.append(candidate.entry)
    return util.append_missing_title_rows(csv_entries, str(csv_path))


def main():
    args = parse_args()
    source_root = Path(args.source_root).expanduser().resolve()
    titles_dir = Path(args.titles_dir).expanduser().resolve()
    csv_path = Path(args.csv).expanduser().resolve()
    report_path = Path(args.report).expanduser().resolve()
    metadata_cache_path = Path(args.metadata_cache).expanduser().resolve()
    archive_cache_path = Path(args.archive_cache).expanduser().resolve()

    rows = load_csv_rows(csv_path)
    existing_by_archive, _ = build_existing_indexes(rows)
    metadata_cache = load_json(metadata_cache_path, {})
    archive_cache = load_json(archive_cache_path, {})
    candidates = [
        build_candidate(archive_path, existing_by_archive, archive_cache)
        for archive_path in list_manual_archives(source_root)
    ]
    if not args.skip_online:
        candidates, metadata_cache = enrich_candidates_online(candidates, metadata_cache)
        save_json(metadata_cache_path, metadata_cache)
    save_json(archive_cache_path, archive_cache)
    write_report(candidates, report_path)

    if args.apply:
        added, updated, _ = apply_candidates(candidates, titles_dir, csv_path)
        print(f"Applied {added} new row(s), updated {updated} existing row(s)")

    ready = sum(1 for candidate in candidates if candidate.status == "ready")
    review = sum(1 for candidate in candidates if candidate.status == "manual-review")
    indexed = sum(1 for candidate in candidates if candidate.status == "already-indexed")
    deferred = sum(1 for candidate in candidates if candidate.status == "deferred-adf")
    print(f"Scanned {len(candidates)} archive(s): {ready} ready, {review} manual-review, {deferred} deferred-adf, {indexed} already-indexed")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
