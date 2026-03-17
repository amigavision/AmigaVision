#!/usr/bin/env python3

import argparse
import csv
import html
import json
import re
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

from ags_screenshot import iff_screenshot


LOWRES_CROP = (640, 512)
LOWRES_SCALE = (320, 256)
LOWRES_RESAMPLE = (320, 128)
LOWRES_COLORS = 128

HIGHRES_CROP = (640, 512)
HIGHRES_SCALE = (360, 288)
HIGHRES_RESAMPLE = (360, 288)
HIGHRES_COLORS = 256

ORDER_RE = re.compile(r"^(?P<index>\d+)(?:[ _.-].*)?$")
LEMON_SCREENSHOT_RE = re.compile(r"(?P<url>(?:https://www\.lemonamiga\.com)?/uploads/amiga/images/games/screens/[^\"'\s>]+)", re.IGNORECASE)
DEMOZOO_SCREENSHOT_RE = re.compile(
    r'(?P<url>https://media\.demozoo\.org/screens/o/[^"\'>\s]+)|"original_url":\s*"(?P<json>https://media\.demozoo\.org/screens/o/[^"]+)"',
    re.IGNORECASE,
)
POUET_SCREENSHOT_RE = re.compile(r'https://content\.pouet\.net/files/screenshots/[^"\'\)\s]+', re.IGNORECASE)
ABIME_SCREENSHOT_RE = re.compile(
    r'(?P<url>(?:https://amiga\.abime\.net)?/screen/[^"\'\s>]+)|<meta\s+property="og:image"\s+content="(?P<og>https://amiga\.abime\.net/screen/[^"]+)"',
    re.IGNORECASE,
)
EXOTICA_RESULT_RE = re.compile(r"<div class='mw-search-result-heading'><a href=\"(?P<href>/wiki/[^\"]+)\" title=\"(?P<title>[^\"]+)\"", re.IGNORECASE)
EXOTICA_IMAGE_RE = re.compile(r'<a href="/wiki/File:[^"]+" class="image"[^>]*><img[^>]+src="(?P<src>/mediawiki/files/[^"]+)"[^>]+width="(?P<width>\d+)"[^>]+height="(?P<height>\d+)"', re.IGNORECASE)
ITCH_RESULT_RE = re.compile(r'<a class="title game_link"[^>]+href="(?P<href>https://[^"]+)"[^>]*>(?P<title>.*?)</a>', re.IGNORECASE)
ITCH_OG_IMAGE_RE = re.compile(r'<meta content="(?P<url>https://img\.itch\.zone/[^"]+)" property="og:image"/>', re.IGNORECASE)
ITCH_SCREENSHOT_RE = re.compile(r'<a data-image_lightbox="true"[^>]+href="(?P<url>https://img\.itch\.zone/[^"]+)"', re.IGNORECASE)
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
TITLE_WORD_RE = re.compile(r"[A-Za-z0-9]+")
STOPWORDS = {"the", "a", "an", "of", "and", "for", "to", "amiga", "edition", "demo", "datadisk", "data", "disk"}
GENERIC_IMAGE_RE = re.compile(r'https?://[^"\'\s>]+\.(?:png|jpg|jpeg|webp)', re.IGNORECASE)

MANUAL_FETCH_OVERRIDES = {
    "game--piracydeluxe--piracydeluxe": {
        "source": "GamesThatWeren't",
        "url": "https://www.gamesthatwerent.com/2025/12/piracy-deluxe/",
        "extractor": "gamesthatwerent",
    },
    "game--vectorbattleground--vectorbattleground": {
        "source": "LaunchBox",
        "url": "https://gamesdb.launchbox-app.com/games/images/407776-vector-battleground",
        "extractor": "launchbox",
    },
    "game--evilsdoomaga--evilsdoomaga": {
        "source": "Video Games Museum",
        "url": "https://www.video-games-museum.com/en/game/Evils-Doom/82/3/72527",
        "extractor": "video_games_museum",
    },
    "game--musclesaga--musclesaga": {
        "source": "YouTube thumbnail",
        "urls": ["https://i.ytimg.com/vi/i8b0LwjaIyA/maxresdefault.jpg"],
    },
    "game--impossiblepossibilityaga--impossiblepossibilityaga": {
        "source": "Demozoo",
        "url": "https://demozoo.org/productions/28441/screenshots/",
        "extractor": "demozoo",
    },
    "game--swos2526--swos2526": {
        "source": "existing SWOS screenshots",
        "copy_from_id": "game--swos--swos",
    },
}

MANUAL_LEMON_URLS = {
    "game--kcmunchkin--kcmunchkin": "https://www.lemonamiga.com/game/k-c-munchkin",
    "game--dylandog05it--dylandog05it": "https://www.lemonamiga.com/game/dylan-dog-05-la-mummia",
    "game--dungeonsofavalon2de--dungeonsofavalon2de": "https://www.lemonamiga.com/game/dungeons-of-avalon-2-the-island-of-darkness",
    "game--diabolik04it--diabolik04it": "https://www.lemonamiga.com/game/diabolik-04-trappola-d-acciaio",
    "game--diabolik10it--diabolik10it": "https://www.lemonamiga.com/game/diabolik-10-all-ultimo-sangue",
    "game--ums--ums": "https://www.lemonamiga.com/game/ums-universal-military-simulator",
}

MANUAL_ABIME_URLS = {
    "game--agresorpl--agresorpl": "https://amiga.abime.net/games/view/agresor",
    "game--diabolik12it--diabolik12it": "https://amiga.abime.net/games/view/diabolik-12-terrore-a-teatro",
    "game--discovery&datadisksmi--discoverymi": "https://amiga.abime.net/games/view/discovery-microillusions",
    "game--frutispl--frutispl": "https://amiga.abime.net/games/view/frutis",
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="data/db/titles.csv")
    parser.add_argument("--downloads-dir", default="data/img_downloads")
    parser.add_argument("--img-dir", default="data/img")
    parser.add_argument("--img-highres-dir", default="data/img_highres")
    parser.add_argument("--unprocessed-dir", default="data/img_highres/Unprocessed")
    parser.add_argument("--chrome-downloads-dir", default=str(Path.home() / "Downloads"))
    parser.add_argument("--fetch-lemon-interactive", action="store_true")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def load_rows(csv_path):
    with open(csv_path, "r") as f:
        return list(csv.DictReader(f, delimiter=";"))


def ordered_images(stage_dir):
    images = sorted(p for p in stage_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)
    ordered = []
    used = set()
    auto_index = 1
    for path in images:
        match = ORDER_RE.match(path.stem)
        if match:
            index = int(match.group("index"))
            ordered.append((index, path))
            used.add(index)
    for path in images:
        match = ORDER_RE.match(path.stem)
        if match:
            continue
        while auto_index in used:
            auto_index += 1
        ordered.append((auto_index, path))
        used.add(auto_index)
        auto_index += 1
    return sorted(ordered)


def fetch_url(url, headers=None):
    request_headers = {"User-Agent": "Mozilla/5.0"}
    if headers:
        request_headers.update(headers)
    req = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read(), response.headers.get_content_type()


def fetch_text(url):
    data, _ = fetch_url(url)
    return data.decode("utf-8", "ignore")


def fetch_text_with_headers(url, headers):
    data, _ = fetch_url(url, headers=headers)
    return data.decode("utf-8", "ignore")


def unique_urls(urls):
    seen = set()
    result = []
    for url in urls:
        if not url or url in seen:
            continue
        seen.add(url)
        result.append(url)
    return result


def normalize_title(text):
    text = html.unescape(text or "")
    words = [word.lower() for word in TITLE_WORD_RE.findall(text)]
    return [word for word in words if word not in STOPWORDS]


def title_match_score(query, candidate):
    query_words = set(normalize_title(query))
    candidate_words = set(normalize_title(candidate))
    if not query_words or not candidate_words:
        return 0.0
    overlap = len(query_words & candidate_words)
    if not overlap:
        return 0.0
    return overlap / max(len(query_words), len(candidate_words))


def pick_best_title_match(query, candidates, minimum_score=0.6):
    best = None
    best_score = 0.0
    for candidate in candidates:
        score = title_match_score(query, candidate["title"])
        if score > best_score:
            best = candidate
            best_score = score
    if best and best_score >= minimum_score:
        return best
    return None


CHROME_APP = "Google Chrome"


def run_osascript(lines):
    cmd = ["osascript"]
    for line in lines:
        cmd.extend(["-e", line])
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout).strip())
    return (proc.stdout or "").strip()


def chrome_open(url):
    run_osascript([
        f'tell application "{CHROME_APP}" to activate',
        f'tell application "{CHROME_APP}" to if (count of windows) is 0 then make new window',
        f'tell application "{CHROME_APP}" to open location "{url}"',
    ])
    time.sleep(1)


def chrome_close_active_tab():
    run_osascript([
        f'tell application "{CHROME_APP}" to if (count of windows) > 0 then close active tab of front window',
    ])


def chrome_source():
    script = 'tell application "Google Chrome" to tell active tab of front window to execute javascript "document.documentElement.outerHTML"'
    return run_osascript([script])


def chrome_execute_javascript(js):
    escaped = js.replace("\\", "\\\\").replace('"', '\\"')
    script = f'tell application "Google Chrome" to tell active tab of front window to execute javascript "{escaped}"'
    return run_osascript([script])


def chrome_download(url, filename):
    js = """
(async function() {
  const response = await fetch(%(url)s, { credentials: 'include' });
  if (!response.ok) return 'HTTP ' + response.status;
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = objectUrl;
  a.download = %(filename)s;
  document.body.appendChild(a);
  a.click();
  setTimeout(function() { URL.revokeObjectURL(objectUrl); a.remove(); }, 1000);
  return 'OK';
})();
""" % {
        "url": json.dumps(url),
        "filename": json.dumps(filename),
    }
    return chrome_execute_javascript(js)


def wait_for_download(downloads_dir, filename, timeout=30):
    downloads_dir = Path(downloads_dir)
    target = downloads_dir / filename
    partial = downloads_dir / f"{filename}.crdownload"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if target.exists() and not partial.exists():
            return target
        time.sleep(0.5)
    return None


def extension_for_content_type(content_type):
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }.get(content_type, ".png")


def extension_from_url(url, default=".png"):
    ext = Path(urllib.parse.urlparse(url).path).suffix.lower()
    return ext if ext in IMAGE_EXTENSIONS else default


def import_unprocessed_images(entries, unprocessed_dir):
    unprocessed_dir = Path(unprocessed_dir)
    if not unprocessed_dir.is_dir():
        return 0
    entry_map = {entry["id"]: entry for entry in entries if not entry["staged"]}
    imported = 0
    for path in sorted(unprocessed_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        stem = path.stem
        if "-" not in stem:
            continue
        entry_id, _, index = stem.rpartition("-")
        if not index.isdigit():
            continue
        entry = entry_map.get(entry_id)
        if not entry:
            continue
        stage_dir = entry["stage_dir"]
        stage_dir.mkdir(parents=True, exist_ok=True)
        dest = stage_dir / f"{index}{path.suffix.lower()}"
        if dest.exists():
            continue
        path.replace(dest)
        imported += 1
    return imported


def stage_downloaded_images(entry, urls):
    stage_dir = entry["stage_dir"]
    stage_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for index, url in enumerate(urls[:6], start=2):
        data, content_type = fetch_url(url)
        ext = extension_for_content_type(content_type) if content_type else extension_from_url(url)
        out_path = stage_dir / f"{index}{ext}"
        out_path.write_bytes(data)
        written.append(out_path.name)
    return written


def extract_demozoo_page_images(page_html):
    images = []
    for match in DEMOZOO_SCREENSHOT_RE.finditer(page_html):
        url = html.unescape(match.group("url") or match.group("json") or "")
        if url and url not in images:
            images.append(url)
    return images[:6]


def extract_gamesthatwerent_images(page_html):
    urls = []
    for url in GENERIC_IMAGE_RE.findall(page_html):
        lowered = url.lower()
        if "wp-content/uploads" not in lowered:
            continue
        if "site-icon" in lowered or "gtw-icon" in lowered:
            continue
        if re.search(r"-\d+x\d+\.(png|jpg|jpeg|webp)$", lowered):
            continue
        urls.append(url)
    return unique_urls(urls)[:6]


def extract_launchbox_images(page_html):
    return unique_urls(
        url for url in GENERIC_IMAGE_RE.findall(page_html)
        if "images.launchbox-app.com/" in url.lower()
    )[:6]


def extract_video_games_museum_images(page_html):
    return unique_urls(
        url for url in GENERIC_IMAGE_RE.findall(page_html)
        if "/screenshots/amiga/" in url.lower()
    )[:6]


def extract_override_images(page_html, extractor):
    if extractor == "demozoo":
        return extract_demozoo_page_images(page_html)
    if extractor == "gamesthatwerent":
        return extract_gamesthatwerent_images(page_html)
    if extractor == "launchbox":
        return extract_launchbox_images(page_html)
    if extractor == "video_games_museum":
        return extract_video_games_museum_images(page_html)
    return []


def apply_manual_copy_overrides(entries, img_dir, img_highres_dir):
    copied = []
    for entry in entries:
        override = MANUAL_FETCH_OVERRIDES.get(entry["id"])
        if not override or "copy_from_id" not in override:
            continue
        source_id = override["copy_from_id"]
        source_lowres = img_dir / f"{source_id}.iff"
        if not source_lowres.exists():
            continue
        dest_lowres = img_dir / f"{entry['id']}.iff"
        if not dest_lowres.exists():
            dest_lowres.write_bytes(source_lowres.read_bytes())
        copied_highres = []
        for src in sorted(img_highres_dir.glob(f"{source_id}-*.iff")):
            _, _, suffix = src.stem.rpartition("-")
            if not suffix.isdigit():
                continue
            dest = img_highres_dir / f"{entry['id']}-{suffix}.iff"
            if not dest.exists():
                dest.write_bytes(src.read_bytes())
            copied_highres.append(dest.name)
        copied.append((entry["id"], source_id, copied_highres))
    return copied


def fetch_manual_override_images(entries):
    fetched = []
    skipped = []
    fetchable_entries = [entry for entry in entries if not entry["staged"] and entry["id"] in MANUAL_FETCH_OVERRIDES]
    total = len(fetchable_entries)
    if total:
        print(f"Fetching manual-source images for {total} remaining title(s)...")
    for i, entry in enumerate(fetchable_entries, start=1):
        override = MANUAL_FETCH_OVERRIDES[entry["id"]]
        if "copy_from_id" in override:
            continue
        page_url = override.get("url")
        image_urls = override.get("urls", [])
        try:
            if page_url and not image_urls:
                page_html = fetch_text(page_url)
                image_urls = extract_override_images(page_html, override["extractor"])
        except Exception as err:
            skipped.append((entry["id"], f"{override['source']} lookup failed: {err}"))
            continue
        if not image_urls:
            skipped.append((entry["id"], f"no {override['source']} screenshots found"))
            continue
        try:
            written = stage_downloaded_images(entry, image_urls)
        except Exception as err:
            skipped.append((entry["id"], f"{override['source']} image fetch failed: {err}"))
            continue
        print(f"[{i}/{total}] {entry['id']} - {entry['title']}")
        if page_url:
            print(f"  page: {page_url}")
        print(f"  downloaded: {', '.join(written)}")
        fetched.append((entry["id"], page_url or override["source"], written))
    return fetched, skipped


def fetch_demozoo_images(entries):
    fetched = []
    skipped = []
    fetchable_entries = [entry for entry in entries if entry["category"] == "Demo" and not entry["staged"] and (entry.get("demozoo_id") or "").strip()]
    total = len(fetchable_entries)
    if total:
        print(f"Fetching Demozoo images for {total} missing demo title(s)...")
    for i, entry in enumerate(fetchable_entries, start=1):
        demozoo_id = entry["demozoo_id"].strip()
        page_url = f"https://demozoo.org/productions/{demozoo_id}/"
        try:
            page_html = fetch_text(page_url)
        except Exception as err:
            skipped.append((entry["id"], f"Demozoo page lookup failed: {err}"))
            continue
        image_urls = extract_demozoo_page_images(page_html)
        if not image_urls:
            skipped.append((entry["id"], "no Demozoo screenshots found"))
            continue
        stage_dir = entry["stage_dir"]
        stage_dir.mkdir(parents=True, exist_ok=True)
        written = []
        for index, url in enumerate(image_urls[:6], start=2):
            try:
                data, content_type = fetch_url(url)
            except Exception as err:
                skipped.append((entry["id"], f"Demozoo image fetch failed: {err}"))
                written = []
                break
            ext = extension_for_content_type(content_type)
            out_path = stage_dir / f"{index}{ext}"
            out_path.write_bytes(data)
            written.append(out_path.name)
        if written:
            print(f"[{i}/{total}] {entry['id']} - {entry['title']}")
            print(f"  page: {page_url}")
            print(f"  downloaded: {', '.join(written)}")
            fetched.append((entry["id"], page_url, written))
    return fetched, skipped


def fetch_pouet_images(entries):
    fetched = []
    skipped = []
    fetchable_entries = [entry for entry in entries if entry["category"] == "Demo" and not entry["staged"] and (entry.get("pouet_id") or "").strip()]
    total = len(fetchable_entries)
    if total:
        print(f"Fetching Pouet images for {total} remaining demo title(s)...")
    for i, entry in enumerate(fetchable_entries, start=1):
        pouet_id = entry["pouet_id"].strip()
        page_url = f"https://www.pouet.net/prod.php?which={pouet_id}"
        try:
            page_html = fetch_text(page_url)
        except Exception as err:
            skipped.append((entry["id"], f"Pouet page lookup failed: {err}"))
            continue
        image_urls = []
        for url in POUET_SCREENSHOT_RE.findall(page_html):
            if url not in image_urls:
                image_urls.append(url)
        if not image_urls:
            skipped.append((entry["id"], "no Pouet screenshots found"))
            continue
        stage_dir = entry["stage_dir"]
        stage_dir.mkdir(parents=True, exist_ok=True)
        written = []
        for index, url in enumerate(image_urls[:6], start=2):
            try:
                data, content_type = fetch_url(url)
            except Exception as err:
                skipped.append((entry["id"], f"Pouet image fetch failed: {err}"))
                written = []
                break
            ext = extension_for_content_type(content_type)
            out_path = stage_dir / f"{index}{ext}"
            out_path.write_bytes(data)
            written.append(out_path.name)
        if written:
            print(f"[{i}/{total}] {entry['id']} - {entry['title']}")
            print(f"  page: {page_url}")
            print(f"  downloaded: {', '.join(written)}")
            fetched.append((entry["id"], page_url, written))
    return fetched, skipped


def resolve_exotica_page(title):
    headers = {"Cookie": "verified=1"}
    direct_url = f"https://www.exotica.org.uk/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
    page_html = fetch_text_with_headers(direct_url, headers)
    if '<div class="searchresults">' not in page_html and "<h1" in page_html:
        return direct_url, page_html

    search_url = "https://www.exotica.org.uk/mediawiki/index.php?" + urllib.parse.urlencode({
        "title": "Special:Search",
        "search": title,
        "fulltext": "1",
    })
    search_html = fetch_text_with_headers(search_url, headers)
    candidates = [
        {
            "href": urllib.parse.urljoin("https://www.exotica.org.uk", html.unescape(match.group("href"))),
            "title": html.unescape(match.group("title")),
        }
        for match in EXOTICA_RESULT_RE.finditer(search_html)
    ]
    best = pick_best_title_match(title, candidates)
    if not best:
        return None, None
    return best["href"], fetch_text_with_headers(best["href"], headers)


def extract_exotica_images(page_html):
    images = []
    for match in EXOTICA_IMAGE_RE.finditer(page_html):
        width = int(match.group("width"))
        height = int(match.group("height"))
        if width < 100 or height < 75:
            continue
        url = urllib.parse.urljoin("https://www.exotica.org.uk", html.unescape(match.group("src")))
        if url not in images:
            images.append(url)
    return [(offset, url) for offset, url in enumerate(images[:6], start=2)]


def fetch_exotica_images(entries):
    fetched = []
    skipped = []
    fetchable_entries = [entry for entry in entries if entry["category"] == "Demo" and not entry["staged"]]
    total = len(fetchable_entries)
    if total:
        print(f"Fetching Exotica images for {total} remaining demo title(s)...")
    for i, entry in enumerate(fetchable_entries, start=1):
        try:
            page_url, page_html = resolve_exotica_page(entry["title"])
        except Exception as err:
            skipped.append((entry["id"], f"Exotica lookup failed: {err}"))
            continue
        if not page_url or not page_html:
            skipped.append((entry["id"], "no Exotica page match"))
            continue
        images = extract_exotica_images(page_html)
        if not images:
            skipped.append((entry["id"], "no Exotica screenshots found"))
            continue
        stage_dir = entry["stage_dir"]
        stage_dir.mkdir(parents=True, exist_ok=True)
        written = []
        for index, url in images:
            try:
                data, content_type = fetch_url(url, {"Cookie": "verified=1"})
            except Exception as err:
                skipped.append((entry["id"], f"Exotica image fetch failed: {err}"))
                written = []
                break
            ext = extension_for_content_type(content_type)
            out_path = stage_dir / f"{index}{ext}"
            out_path.write_bytes(data)
            written.append(out_path.name)
        if written:
            print(f"[{i}/{total}] {entry['id']} - {entry['title']}")
            print(f"  page: {page_url}")
            print(f"  downloaded: {', '.join(written)}")
            fetched.append((entry["id"], page_url, written))
    return fetched, skipped


def resolve_itch_page(title):
    search_url = "https://itch.io/search?" + urllib.parse.urlencode({"q": f"{title} amiga", "type": "games"})
    search_html = fetch_text(search_url)
    candidates = [
        {
            "href": html.unescape(match.group("href")),
            "title": html.unescape(re.sub(r"<[^>]+>", "", match.group("title"))),
        }
        for match in ITCH_RESULT_RE.finditer(search_html)
    ]
    best = pick_best_title_match(title, candidates)
    if not best:
        return None, None
    return best["href"], fetch_text(best["href"])


def extract_itch_images(page_html):
    images = []
    og_match = ITCH_OG_IMAGE_RE.search(page_html)
    if og_match:
        images.append(html.unescape(og_match.group("url")))
    for match in ITCH_SCREENSHOT_RE.finditer(page_html):
        url = html.unescape(match.group("url"))
        if url not in images:
            images.append(url)
    return [(offset, url) for offset, url in enumerate(images[:6], start=2)]


def fetch_itch_images(entries):
    fetched = []
    skipped = []
    fetchable_entries = [entry for entry in entries if entry["category"] == "Game" and not entry["staged"]]
    total = len(fetchable_entries)
    if total:
        print(f"Fetching itch.io images for {total} remaining game title(s)...")
    for i, entry in enumerate(fetchable_entries, start=1):
        try:
            page_url, page_html = resolve_itch_page(entry["title"])
        except Exception as err:
            skipped.append((entry["id"], f"itch.io lookup failed: {err}"))
            continue
        if not page_url or not page_html:
            skipped.append((entry["id"], "no itch.io page match"))
            continue
        images = extract_itch_images(page_html)
        if not images:
            skipped.append((entry["id"], "no itch.io screenshots found"))
            continue
        stage_dir = entry["stage_dir"]
        stage_dir.mkdir(parents=True, exist_ok=True)
        written = []
        for index, url in images:
            try:
                data, content_type = fetch_url(url)
            except Exception as err:
                skipped.append((entry["id"], f"itch.io image fetch failed: {err}"))
                written = []
                break
            ext = extension_for_content_type(content_type or extension_from_url(url))
            out_path = stage_dir / f"{index}{ext}"
            out_path.write_bytes(data)
            written.append(out_path.name)
        if written:
            print(f"[{i}/{total}] {entry['id']} - {entry['title']}")
            print(f"  page: {page_url}")
            print(f"  downloaded: {', '.join(written)}")
            fetched.append((entry["id"], page_url, written))
    return fetched, skipped


def extract_lemon_images(page_html):
    screenshots = []
    for match in LEMON_SCREENSHOT_RE.finditer(page_html):
        full = urllib.parse.urljoin("https://www.lemonamiga.com", html.unescape(match.group("url")))
        if full not in screenshots:
            screenshots.append(full)
    images = []
    for offset, url in enumerate(screenshots, start=2):
        if offset > 7:
            break
        images.append((offset, url))
    return images


def extract_abime_images(page_html):
    screenshots = []
    for match in ABIME_SCREENSHOT_RE.finditer(page_html):
        url = html.unescape(match.group("url") or match.group("og") or "")
        if url:
            url = urllib.parse.urljoin("https://amiga.abime.net", url)
        if url not in screenshots:
            screenshots.append(url)
    images = []
    for offset, url in enumerate(screenshots, start=2):
        if offset > 7:
            break
        images.append((offset, url))
    return images


def fetch_lemon_interactive_images(entries, chrome_downloads_dir):
    fetchable_entries = [
        entry for entry in entries
        if entry["category"] == "Game"
        and not entry["staged"]
        and ((entry.get("lemon_id") or "").strip() or entry["id"] in MANUAL_LEMON_URLS)
    ]
    return fetch_browser_interactive_images(
        fetchable_entries,
        chrome_downloads_dir,
        "Lemon Amiga",
        lambda entry: MANUAL_LEMON_URLS.get(entry["id"]) or f"https://www.lemonamiga.com/?game_id={entry['lemon_id'].strip()}",
        lemon_page_ready,
        extract_lemon_images,
    )


def fetch_abime_interactive_images(entries, chrome_downloads_dir):
    fetchable_entries = [
        entry for entry in entries
        if entry["category"] == "Game"
        and not entry["staged"]
        and entry["id"] in MANUAL_ABIME_URLS
    ]
    return fetch_browser_interactive_images(
        fetchable_entries,
        chrome_downloads_dir,
        "abime",
        lambda entry: MANUAL_ABIME_URLS[entry["id"]],
        abime_page_ready,
        extract_abime_images,
    )


def fetch_browser_interactive_images(entries, chrome_downloads_dir, source_name, page_url_for_entry, page_ready_fn, extract_images_fn):
    fetched = []
    skipped = []
    total = len(entries)
    if not total:
        return fetched, skipped
    print(f"Fetching {source_name} images interactively for {total} title(s)...")
    print(f"Chrome will open {source_name} pages. If protection appears, solve it in Chrome, then return to the terminal and press Enter to continue.")
    print("Chrome also needs View > Developer > Allow JavaScript from Apple Events enabled so the script can read the page afterward.")
    print(f"Downloaded {source_name} screenshots are pulled from {chrome_downloads_dir} after Chrome saves them.")
    print()
    for i, entry in enumerate(entries, start=1):
        page_url = page_url_for_entry(entry)
        print(f"[{i}/{total}] {entry['id']} - {entry['title']}")
        print(f"  page: {page_url}")
        try:
            try:
                chrome_open(page_url)
            except Exception as err:
                print(f"  skipped: could not open Chrome page: {err}")
                skipped.append((entry["id"], f"could not open Chrome page: {err}"))
                continue
            try:
                page_html = wait_for_page(page_ready_fn)
            except Exception as err:
                msg = str(err)
                if "Allow JavaScript from Apple Events" in msg:
                    raise SystemExit("Chrome is not ready for interactive scraping. Enable View > Developer > Allow JavaScript from Apple Events and rerun.")
                print(f"  skipped: could not read Chrome page: {err}")
                skipped.append((entry["id"], f"could not read Chrome page: {err}"))
                continue
            if not page_ready_fn(page_html):
                answer = input(f"  page still blocked; solve {source_name} protection in Chrome, then press Enter to continue or type 's' to skip: ").strip().lower()
                if answer == "s":
                    print("  skipped: manually skipped")
                    skipped.append((entry["id"], "manually skipped"))
                    continue
                try:
                    page_html = wait_for_page_after_manual_retry(page_ready_fn)
                except Exception as err:
                    msg = str(err)
                    if "Allow JavaScript from Apple Events" in msg:
                        raise SystemExit("Chrome is not ready for interactive scraping. Enable View > Developer > Allow JavaScript from Apple Events and rerun.")
                    print(f"  skipped: could not read Chrome page: {err}")
                    skipped.append((entry["id"], f"could not read Chrome page: {err}"))
                    continue
                if not page_ready_fn(page_html):
                    print("  skipped: protection still active")
                    skipped.append((entry["id"], "protection still active"))
                    continue
            image_urls = extract_images_fn(page_html)
            if not image_urls:
                print(f"  skipped: no {source_name} screenshots found")
                skipped.append((entry["id"], f"no {source_name} screenshots found"))
                continue
            stage_dir = entry["stage_dir"]
            stage_dir.mkdir(parents=True, exist_ok=True)
            written = []
            for index, url in image_urls:
                ext = Path(urllib.parse.urlparse(url).path).suffix.lower() or ".png"
                if ext not in IMAGE_EXTENSIONS:
                    ext = ".png"
                browser_name = f"{entry['id']}-{index}{ext}"
                try:
                    result = chrome_download(url, browser_name)
                except Exception as err:
                    print(f"  skipped: image download trigger failed: {err}")
                    skipped.append((entry["id"], f"image download trigger failed: {err}"))
                    written = []
                    break
                if result and result != "OK":
                    print(f"  skipped: image download blocked: {result}")
                    skipped.append((entry["id"], f"image download blocked: {result}"))
                    written = []
                    break
                downloaded = wait_for_download(chrome_downloads_dir, browser_name)
                if not downloaded:
                    print("  skipped: Chrome download did not complete")
                    skipped.append((entry["id"], "Chrome download did not complete"))
                    written = []
                    break
                out_path = stage_dir / f"{index}{ext}"
                downloaded.replace(out_path)
                written.append(out_path.name)
            if written:
                print(f"  downloaded: {', '.join(written)}")
                fetched.append((entry["id"], page_url, written))
        finally:
            try:
                chrome_close_active_tab()
            except Exception:
                pass
    return fetched, skipped




def lemon_page_ready(page_html):
    if not page_html:
        return False
    lowered = page_html.lower()
    if "just a moment" in lowered or "challenge-platform" in lowered or "cf-challenge" in lowered:
        return False
    return "/uploads/amiga/images/games/screens/" in lowered or "lemonamiga" in lowered


def abime_page_ready(page_html):
    if not page_html:
        return False
    lowered = page_html.lower()
    if "anubis" in lowered or "making sure you're not a bot" in lowered or "techaro" in lowered:
        return False
    return "/games/screens/" in lowered or "amiga.abime.net/games/view/" in lowered


def wait_for_lemon_page():
    for _ in range(5):
        try:
            page_html = chrome_source()
        except Exception:
            time.sleep(1)
            continue
        if lemon_page_ready(page_html):
            return page_html
        time.sleep(1)
    return chrome_source()


def wait_for_lemon_page_after_manual_retry():
    for _ in range(20):
        page_html = chrome_source()
        if lemon_page_ready(page_html):
            return page_html
        time.sleep(1)
    return chrome_source()


def wait_for_page(check_fn, attempts=5, interval=1):
    for _ in range(attempts):
        try:
            page_html = chrome_source()
        except Exception:
            time.sleep(interval)
            continue
        if check_fn(page_html):
            return page_html
        time.sleep(interval)
    return chrome_source()


def wait_for_page_after_manual_retry(check_fn, attempts=20, interval=1):
    for _ in range(attempts):
        page_html = chrome_source()
        if check_fn(page_html):
            return page_html
        time.sleep(interval)
    return chrome_source()


def write_iff(src_path, out_path, colors, crop, scale, resample):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    iff_data, _ = iff_screenshot(str(src_path), colors, crop, scale, resample)
    with open(out_path, "wb") as f:
        f.write(iff_data)


def lowres_source_index(indices):
    if 2 in indices:
        return 2
    if 3 in indices:
        return 3
    return min(indices) if indices else None


def collect_missing(rows, img_dir, img_highres_dir, downloads_dir):
    highres_counts = {}
    for path in img_highres_dir.glob("*.iff"):
        if path.name.startswith("!"):
            continue
        stem = path.stem
        if "-" not in stem:
            continue
        id_stem, _, suffix = stem.rpartition("-")
        if not suffix.isdigit():
            continue
        highres_counts[id_stem] = highres_counts.get(id_stem, 0) + 1

    entries = []
    for row in rows:
        if not row.get("archive_path"):
            continue
        id_ = row["id"]
        lowres_path = img_dir / f"{id_}.iff"
        stage_dir = downloads_dir / id_
        staged = ordered_images(stage_dir) if stage_dir.is_dir() else []
        if not lowres_path.is_file():
            entries.append({
                "id": id_,
                "title": row.get("title", ""),
                "category": row.get("category", ""),
                "subcategory": row.get("subcategory", ""),
                "lowres_exists": False,
                "highres_count": highres_counts.get(id_, 0),
                "stage_dir": stage_dir,
                "staged": staged,
                "hol_id": row.get("hol_id", ""),
                "lemon_id": row.get("lemon_id", ""),
                "demozoo_id": row.get("demozoo_id", ""),
                "pouet_id": row.get("pouet_id", ""),
            })
    return entries


def sync_images(entries, img_dir, img_highres_dir):
    converted = []
    skipped = []
    for entry in entries:
        staged = entry["staged"]
        if not staged:
            continue
        indices = [index for index, _ in staged]
        lowres_index = lowres_source_index(indices)
        if lowres_index is None:
            skipped.append((entry["id"], "no usable PNG order"))
            continue
        stage_by_index = dict(staged)
        lowres_src = stage_by_index[lowres_index]

        lowres_dest = img_dir / f"{entry['id']}.iff"
        write_iff(lowres_src, lowres_dest, LOWRES_COLORS, LOWRES_CROP, LOWRES_SCALE, LOWRES_RESAMPLE)

        written_highres = []
        for index, src in staged:
            highres_dest = img_highres_dir / f"{entry['id']}-{index}.iff"
            write_iff(src, highres_dest, HIGHRES_COLORS, HIGHRES_CROP, HIGHRES_SCALE, HIGHRES_RESAMPLE)
            written_highres.append(highres_dest.name)

        converted.append((entry["id"], lowres_src.name, written_highres))
    return converted, skipped


def main():
    args = parse_args()
    csv_path = Path(args.csv)
    downloads_dir = Path(args.downloads_dir)
    img_dir = Path(args.img_dir)
    img_highres_dir = Path(args.img_highres_dir)
    unprocessed_dir = Path(args.unprocessed_dir)

    rows = load_rows(csv_path)
    missing = collect_missing(rows, img_dir, img_highres_dir, downloads_dir)
    imported = import_unprocessed_images(missing, unprocessed_dir)
    if imported:
        print(f"Imported {imported} local unprocessed image(s) into staging")
        rows = load_rows(csv_path)
        missing = collect_missing(rows, img_dir, img_highres_dir, downloads_dir)

    converted = []
    fetched = []
    skipped = []

    copied = apply_manual_copy_overrides(missing, img_dir, img_highres_dir)
    if copied:
        print(f"Copied existing images for {len(copied)} title(s)")
        for id_, source_id, copied_highres in copied:
            detail = f"; highres {', '.join(copied_highres)}" if copied_highres else ""
            print(f"{id_}: from {source_id}{detail}")
        print()
        rows = load_rows(csv_path)
        missing = collect_missing(rows, img_dir, img_highres_dir, downloads_dir)

    fetched, skipped = fetch_manual_override_images(missing)
    if fetched:
        print(f"Fetched manual-source images for {len(fetched)} title(s)")
        for id_, page_url, written in fetched:
            print(f"{id_}: {page_url} -> {', '.join(written)}")
        print()
    if skipped:
        print(f"Skipped {len(skipped)} manual-source fetches")
        print()
    rows = load_rows(csv_path)
    missing = collect_missing(rows, img_dir, img_highres_dir, downloads_dir)
    skipped = []

    fetched, skipped = fetch_demozoo_images(missing)
    if fetched:
        print(f"Fetched Demozoo images for {len(fetched)} title(s)")
        for id_, page_url, written in fetched:
            print(f"{id_}: {page_url} -> {', '.join(written)}")
        print()
    if skipped:
        print(f"Skipped {len(skipped)} Demozoo fetches")
        print()
    rows = load_rows(csv_path)
    missing = collect_missing(rows, img_dir, img_highres_dir, downloads_dir)
    skipped = []

    fetched, skipped = fetch_pouet_images(missing)
    if fetched:
        print(f"Fetched Pouet images for {len(fetched)} title(s)")
        for id_, page_url, written in fetched:
            print(f"{id_}: {page_url} -> {', '.join(written)}")
        print()
    if skipped:
        print(f"Skipped {len(skipped)} Pouet fetches")
        print()
    rows = load_rows(csv_path)
    missing = collect_missing(rows, img_dir, img_highres_dir, downloads_dir)
    skipped = []

    fetched, skipped = fetch_exotica_images(missing)
    if fetched:
        print(f"Fetched Exotica images for {len(fetched)} title(s)")
        for id_, page_url, written in fetched:
            print(f"{id_}: {page_url} -> {', '.join(written)}")
        print()
    if skipped:
        print(f"Skipped {len(skipped)} Exotica fetches")
        print()
    rows = load_rows(csv_path)
    missing = collect_missing(rows, img_dir, img_highres_dir, downloads_dir)
    skipped = []

    if args.fetch_lemon_interactive:
        fetched, skipped = fetch_lemon_interactive_images(missing, args.chrome_downloads_dir)
        if fetched:
            print(f"Fetched Lemon Amiga images for {len(fetched)} title(s)")
            for id_, page_url, written in fetched:
                print(f"{id_}: {page_url} -> {', '.join(written)}")
            print()
        if skipped:
            print(f"Skipped {len(skipped)} Lemon Amiga fetches")
            for id_, reason in skipped:
                print(f"{id_}: {reason}")
            print()
        rows = load_rows(csv_path)
        missing = collect_missing(rows, img_dir, img_highres_dir, downloads_dir)
        skipped = []

        fetched, skipped = fetch_abime_interactive_images(missing, args.chrome_downloads_dir)
        if fetched:
            print(f"Fetched abime images for {len(fetched)} title(s)")
            for id_, page_url, written in fetched:
                print(f"{id_}: {page_url} -> {', '.join(written)}")
            print()
        if skipped:
            print(f"Skipped {len(skipped)} abime fetches")
            for id_, reason in skipped:
                print(f"{id_}: {reason}")
            print()
        rows = load_rows(csv_path)
        missing = collect_missing(rows, img_dir, img_highres_dir, downloads_dir)
        skipped = []

    fetched, skipped = fetch_itch_images(missing)
    if fetched:
        print(f"Fetched itch.io images for {len(fetched)} title(s)")
        for id_, page_url, written in fetched:
            print(f"{id_}: {page_url} -> {', '.join(written)}")
        print()
    if skipped:
        print(f"Skipped {len(skipped)} itch.io fetches")
        print()
    rows = load_rows(csv_path)
    missing = collect_missing(rows, img_dir, img_highres_dir, downloads_dir)
    skipped = []

    if args.apply:
        converted, skipped = sync_images(missing, img_dir, img_highres_dir)
        if converted:
            print(f"Converted {len(converted)} title(s)")
            for id_, lowres_src, highres_written in converted:
                print(f"{id_}: lowres from {lowres_src}; highres {', '.join(highres_written)}")
            print()
        if skipped:
            print(f"Skipped {len(skipped)} title(s)")
            for id_, reason in skipped:
                print(f"{id_}: {reason}")
            print()
        rows = load_rows(csv_path)
        missing = collect_missing(rows, img_dir, img_highres_dir, downloads_dir)

    print(f"Missing low-res images remaining: {len(missing)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
