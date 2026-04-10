#!/usr/bin/env python3

import argparse
import csv
import json
import re
from pathlib import Path

import sync_missing_images as browser


YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
LEMON_FIELD_RE = re.compile(
    r"^(Released|Publisher|Players|Language|Genre|Developer|Developed by):\s*(.+)$"
)
HOL_SECTION_STOPS = {
    "Features",
    "Credits",
    "Enhanced Features",
    "Coding",
    "Graphics",
    "Music",
    "Sound",
    "Sound FX",
    "Speech",
    "Version info",
    "Releases",
    "Links",
    "Stats",
}
UNKNOWN_VALUES = {"", "unknown"}
FIELDS = ("release_date", "publisher", "players", "language", "developer")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Correct game metadata from LemonAmiga first and HoL as fallback."
    )
    parser.add_argument("--csv", default="data/db/titles.csv")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--checkpoint-every-rows",
        type=int,
        default=200,
        help="Rewrite the CSV after this many checked rows when --apply is set",
    )
    parser.add_argument(
        "--checkpoint-every-updates",
        type=int,
        default=25,
        help="Rewrite the CSV after this many changed rows when --apply is set",
    )
    parser.add_argument(
        "--progress-file",
        default="data/cache/fill-missing-metadata-progress.json",
        help="JSON progress file used to resume checked entries across restarts",
    )
    parser.add_argument(
        "--reset-progress",
        action="store_true",
        help="Ignore any saved progress and start from the top again",
    )
    return parser.parse_args()


def load_rows(csv_path):
    with open(csv_path, "r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def write_rows(csv_path, rows):
    if not rows:
        return
    fieldnames = [field for field in rows[0].keys() if field is not None]
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            delimiter=";",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def load_progress(progress_path, reset=False):
    if reset or not progress_path.is_file():
        return {"checked_ids": [], "updated_ids": [], "skipped": {}}
    try:
        data = json.loads(progress_path.read_text(encoding="utf-8"))
    except Exception:
        return {"checked_ids": [], "updated_ids": [], "skipped": {}}
    return {
        "checked_ids": data.get("checked_ids", []),
        "updated_ids": data.get("updated_ids", []),
        "skipped": data.get("skipped", {}),
    }


def write_progress(progress_path, progress):
    progress["checked_ids"] = sorted(set(progress.get("checked_ids", [])))
    progress["updated_ids"] = sorted(set(progress.get("updated_ids", [])))
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.write_text(
        json.dumps(progress, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def normalize_year(text):
    match = YEAR_RE.search(text or "")
    return match.group(0) if match else ""


def normalize_people(text):
    value = re.sub(r"\s+", " ", (text or "").strip())
    if not value or value.lower() == "unknown":
        return ""
    return value


def normalize_language(text):
    value = re.sub(r"\s+", " ", (text or "").strip())
    if not value or value.lower() == "unknown":
        return ""
    return value


def normalize_players(text):
    value = re.sub(r"\s+", " ", (text or "").strip())
    if not value or value.lower() == "unknown" or value == "0":
        return ""
    only_match = re.fullmatch(r"(\d+)\s+Only", value, re.IGNORECASE)
    if only_match:
        return only_match.group(1)
    range_match = re.fullmatch(
        r"(\d+)\s+to\s+(\d+),\s*(Simultaneous|Taking Turns)",
        value,
        re.IGNORECASE,
    )
    if range_match:
        _, maximum, mode = range_match.groups()
        return maximum if mode.lower() == "simultaneous" else f"{maximum} (taking turns)"
    or_match = re.fullmatch(
        r"(\d+)\s+or\s+(\d+),\s*(Simultaneous|Taking Turns)",
        value,
        re.IGNORECASE,
    )
    if or_match:
        _, maximum, mode = or_match.groups()
        return maximum if mode.lower() == "simultaneous" else f"{maximum} (taking turns)"
    max_sim_match = re.fullmatch(r"Max\s+(\d+),\s*Sim\s+(\d+)", value, re.IGNORECASE)
    if max_sim_match:
        maximum, simultaneous = max_sim_match.groups()
        if maximum == simultaneous:
            return maximum
        if simultaneous == "1":
            return f"{maximum} (taking turns)"
        return maximum
    return value


def normalize_field(field, value):
    if field == "release_date":
        return normalize_year(value)
    if field in {"publisher", "developer"}:
        return normalize_people(value)
    if field == "language":
        return normalize_language(value)
    if field == "players":
        return normalize_players(value)
    return re.sub(r"\s+", " ", (value or "").strip())


def comparable_value(field, value):
    normalized = normalize_field(field, value)
    if field == "language":
        return normalized.lower()
    return normalized


def fetch_page_bundle(url, ready_fn, extra_js=None):
    if not url:
        return {"text": "", "extra": ""}
    try:
        browser.chrome_open(url)
        html = browser.wait_for_page(ready_fn, attempts=10, interval=1)
        if not ready_fn(html):
            return {"text": "", "extra": ""}
        return {
            "text": browser.chrome_execute_javascript("document.body.innerText"),
            "extra": browser.chrome_execute_javascript(extra_js) if extra_js else "",
        }
    finally:
        try:
            browser.chrome_close_active_tab()
        except Exception:
            pass


def lemon_url_for_row(row):
    lemon_id = (row.get("lemon_id") or "").strip()
    if row["id"] in browser.MANUAL_LEMON_URLS:
        return browser.MANUAL_LEMON_URLS[row["id"]]
    if lemon_id and lemon_id not in ("0", "-2"):
        return f"https://www.lemonamiga.com/?game_id={lemon_id}"
    return ""


def hol_url_for_row(row):
    hol_id = (row.get("hol_id") or "").strip()
    if row["id"] in browser.MANUAL_ABIME_URLS:
        return browser.MANUAL_ABIME_URLS[row["id"]]
    if hol_id and hol_id not in ("0", "-2"):
        return f"https://hol.abime.net/{hol_id}"
    return ""


def parse_lemon(text):
    result = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = LEMON_FIELD_RE.match(line)
        if not match:
            continue
        field, value = match.groups()
        if field == "Released":
            result["release_date"] = normalize_year(value)
        elif field == "Publisher":
            result["publisher"] = normalize_people(value)
        elif field == "Players":
            result["players"] = normalize_players(value)
        elif field == "Language":
            result["language"] = normalize_language(value)
        elif field in {"Developer", "Developed by"}:
            result["developer"] = normalize_people(value)
    return result


def parse_hol_release_table(extra_json):
    if not extra_json:
        return {}
    try:
        return json.loads(extra_json)
    except Exception:
        return {}


def parse_hol(text, release):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    result = {}
    for idx, line in enumerate(lines):
        if line == "Year" and "release_date" not in result:
            year = normalize_year(" ".join(lines[idx + 1:idx + 3]))
            if year:
                result["release_date"] = year
        elif line == "Players" and "players" not in result and idx + 1 < len(lines):
            players = normalize_players(lines[idx + 1])
            if players:
                result["players"] = players
        elif line == "Developers" and "developer" not in result:
            values = []
            for candidate in lines[idx + 1:]:
                if candidate in HOL_SECTION_STOPS:
                    break
                values.append(candidate)
            developer = normalize_people(", ".join(values))
            if developer:
                result["developer"] = developer
    if release.get("Publisher"):
        result.setdefault("publisher", normalize_people(release.get("Publisher", "")))
    if release.get("Languages"):
        result.setdefault("language", normalize_language(release.get("Languages", "")))
    if release.get("Year"):
        result.setdefault("release_date", normalize_year(release.get("Year", "")))
    return result


def fetch_lemon_metadata(url, cache):
    if not url:
        return {}
    if url not in cache:
        bundle = fetch_page_bundle(url, browser.lemon_page_ready)
        cache[url] = parse_lemon(bundle["text"])
    return cache[url]


def fetch_hol_metadata(url, cache):
    if not url:
        return {}
    if url not in cache:
        bundle = fetch_page_bundle(
            url,
            browser.abime_page_ready,
            extra_js="""JSON.stringify((() => {
                const item = document.querySelector('.release_list_item');
                if (!item) return {};
                const pairs = {};
                const children = Array.from(item.children);
                for (let i = 0; i < children.length - 1; i += 2) {
                    const label = (children[i].innerText || '').trim();
                    const value = (children[i + 1].innerText || '').trim();
                    if (label) pairs[label] = value;
                }
                return pairs;
            })())""",
        )
        cache[url] = parse_hol(bundle["text"], parse_hol_release_table(bundle["extra"]))
    return cache[url]


def combine_site_metadata(row, lemon_cache, hol_cache):
    lemon_url = lemon_url_for_row(row)
    hol_url = hol_url_for_row(row)
    lemon = fetch_lemon_metadata(lemon_url, lemon_cache)
    result = dict(lemon)
    missing_fields = [field for field in FIELDS if not result.get(field)]
    if missing_fields and hol_url:
        hol = fetch_hol_metadata(hol_url, hol_cache)
        for field in missing_fields:
            if hol.get(field):
                result[field] = hol[field]
    return result


def target_rows(rows):
    result = []
    for row in rows:
        if row.get("category") != "Game":
            continue
        if not any(not (row.get(field) or "").strip() for field in FIELDS):
            continue
        if lemon_url_for_row(row) or hol_url_for_row(row):
            result.append(row)
    return result


def maybe_checkpoint(
    csv_path,
    rows,
    progress_path,
    progress,
    checked,
    updated,
    last_checkpoint_checked,
    last_checkpoint_updated,
):
    rows_since_checkpoint = checked - last_checkpoint_checked
    updates_since_checkpoint = updated - last_checkpoint_updated
    if rows_since_checkpoint <= 0 and updates_since_checkpoint <= 0:
        return last_checkpoint_checked, last_checkpoint_updated
    write_rows(csv_path, rows)
    write_progress(progress_path, progress)
    print(
        f"Checkpoint saved at row {checked} with {updated} updated row(s) total"
    )
    return checked, updated


def main():
    args = parse_args()
    csv_path = Path(args.csv)
    progress_path = Path(args.progress_file)
    rows = load_rows(csv_path)
    progress = load_progress(progress_path, reset=args.reset_progress)
    checked_ids = set(progress["checked_ids"])
    updated_ids = set(progress["updated_ids"])
    skipped_ids = dict(progress["skipped"])
    targets = [row for row in target_rows(rows) if row["id"] not in checked_ids]
    if args.limit > 0:
        targets = targets[:args.limit]
    print(
        f"Checking {len(targets)} game row(s) against LemonAmiga and HoL..."
        f" ({len(checked_ids)} already checked)"
    )
    lemon_cache = {}
    hol_cache = {}
    updated = len(updated_ids)
    checked = 0
    skipped = list(skipped_ids.items())
    last_checkpoint_checked = 0
    last_checkpoint_updated = 0
    for row in targets:
        checked += 1
        try:
            site = combine_site_metadata(row, lemon_cache, hol_cache)
        except Exception as err:
            skipped_ids[row["id"]] = str(err)
            progress["skipped"] = skipped_ids
            progress["checked_ids"].append(row["id"])
            skipped.append((row["id"], str(err)))
            print(f"[{checked}/{len(targets)}] {row['id']} -> skipped: {err}")
            if args.apply:
                rows_due = (
                    args.checkpoint_every_rows > 0
                    and checked - last_checkpoint_checked >= args.checkpoint_every_rows
                )
                if rows_due:
                    last_checkpoint_checked, last_checkpoint_updated = maybe_checkpoint(
                        csv_path,
                        rows,
                        progress_path,
                        progress,
                        checked,
                        updated,
                        last_checkpoint_checked,
                        last_checkpoint_updated,
                    )
            continue
        changed = []
        for field in FIELDS:
            current_value = row.get(field, "")
            if (current_value or "").strip():
                continue
            site_value = site.get(field, "")
            if not site_value:
                continue
            row[field] = site_value
            changed.append(f"{field}: {current_value or '(blank)'} -> {site_value}")
        if changed:
            updated_ids.add(row["id"])
            progress["updated_ids"] = sorted(updated_ids)
            updated = len(updated_ids)
            print(f"[{checked}/{len(targets)}] {row['id']} -> " + ", ".join(changed))
        progress["checked_ids"].append(row["id"])
        if args.apply:
            rows_due = (
                args.checkpoint_every_rows > 0
                and checked - last_checkpoint_checked >= args.checkpoint_every_rows
            )
            updates_due = (
                args.checkpoint_every_updates > 0
                and updated - last_checkpoint_updated >= args.checkpoint_every_updates
            )
            if rows_due or updates_due:
                last_checkpoint_checked, last_checkpoint_updated = maybe_checkpoint(
                    csv_path,
                    rows,
                    progress_path,
                    progress,
                    checked,
                    updated,
                    last_checkpoint_checked,
                    last_checkpoint_updated,
                )
    if args.apply and updated:
        if checked != last_checkpoint_checked or updated != last_checkpoint_updated:
            last_checkpoint_checked, last_checkpoint_updated = maybe_checkpoint(
                csv_path,
                rows,
                progress_path,
                progress,
                checked,
                updated,
                last_checkpoint_checked,
                last_checkpoint_updated,
            )
        print(f"\nWrote updates for {updated} row(s) to {csv_path}")
    else:
        print(f"\nUpdated {updated} row(s) in memory")
    print(f"Fetched {len(lemon_cache)} Lemon page(s) and {len(hol_cache)} HoL page(s)")
    if skipped:
        print(f"Skipped {len(skipped)} row(s) due to fetch/parse errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
