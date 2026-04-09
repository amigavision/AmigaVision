#!/usr/bin/env python3

import argparse
import csv
import re
from pathlib import Path

import sync_missing_images as browser


YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def parse_args():
    parser = argparse.ArgumentParser(description="Fill blank game release years from LemonAmiga and HoL pages.")
    parser.add_argument("--csv", default="data/db/titles.csv")
    parser.add_argument("--apply", action="store_true", help="Write recovered years back into the CSV")
    return parser.parse_args()


def load_rows(csv_path):
    with open(csv_path, "r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def write_rows(csv_path, rows):
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=";", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def first_year(text):
    match = YEAR_RE.search(text or "")
    return match.group(0) if match else ""


def extract_lemon_year(page_text):
    for line in page_text.splitlines():
        if line.startswith("Released:"):
            return first_year(line)
    return ""


def extract_hol_year(page_text):
    lines = [line.strip() for line in page_text.splitlines()]
    for idx, line in enumerate(lines):
        if line != "Year":
            continue
        for next_line in lines[idx + 1:idx + 4]:
            year = first_year(next_line)
            if year:
                return year
    return ""


def fetch_page_text(url, ready_fn):
    try:
        browser.chrome_open(url)
        html = browser.wait_for_page(ready_fn, attempts=10, interval=1)
        if not ready_fn(html):
            return ""
        return browser.chrome_execute_javascript("document.body.innerText")
    finally:
        try:
            browser.chrome_close_active_tab()
        except Exception:
            pass


def lemon_url_for_row(row):
    lemon_id = (row.get("lemon_id") or "").strip()
    if row["id"] in browser.MANUAL_LEMON_URLS:
        return browser.MANUAL_LEMON_URLS[row["id"]]
    if lemon_id and lemon_id != "0":
        return f"https://www.lemonamiga.com/?game_id={lemon_id}"
    return ""


def hol_url_for_row(row):
    hol_id = (row.get("hol_id") or "").strip()
    if row["id"] in browser.MANUAL_ABIME_URLS:
        return browser.MANUAL_ABIME_URLS[row["id"]]
    if hol_id and hol_id != "0":
        return f"https://hol.abime.net/{hol_id}"
    return ""


def recover_year(row):
    lemon_year = ""
    hol_year = ""
    lemon_url = lemon_url_for_row(row)
    hol_url = hol_url_for_row(row)
    if lemon_url:
        lemon_year = extract_lemon_year(fetch_page_text(lemon_url, browser.lemon_page_ready))
    if hol_url:
        hol_year = extract_hol_year(fetch_page_text(hol_url, browser.abime_page_ready))
    chosen = lemon_year or hol_year
    conflict = ""
    if lemon_year and hol_year and lemon_year != hol_year:
        conflict = f"Lemon={lemon_year}, HoL={hol_year}"
    if chosen == lemon_year and lemon_year:
        source = "Lemon"
    elif chosen == hol_year and hol_year:
        source = "HoL"
    else:
        source = ""
    return {
        "year": chosen,
        "source": source,
        "conflict": conflict,
        "lemon_url": lemon_url,
        "hol_url": hol_url,
    }


def main():
    args = parse_args()
    csv_path = Path(args.csv)
    rows = load_rows(csv_path)
    target_rows = [
        row for row in rows
        if row.get("category") == "Game"
        and not (row.get("release_date") or "").strip()
        and (lemon_url_for_row(row) or hol_url_for_row(row))
    ]
    print(f"Scanning {len(target_rows)} blank game year row(s)...")
    updated = 0
    unresolved = []
    conflicts = []
    for index, row in enumerate(target_rows, start=1):
        result = recover_year(row)
        label = f"[{index}/{len(target_rows)}] {row['id']}"
        if result["year"]:
            print(f"{label} -> {result['year']} ({result['source']})")
            row["release_date"] = result["year"]
            updated += 1
            if result["conflict"]:
                conflicts.append((row["id"], result["conflict"]))
        else:
            print(f"{label} -> unresolved")
            unresolved.append(row["id"])
    if args.apply and updated:
        write_rows(csv_path, rows)
        print(f"\nWrote {updated} recovered year(s) to {csv_path}")
    else:
        print(f"\nRecovered {updated} year(s)")
    if conflicts:
        print("\nConflicts:")
        for row_id, detail in conflicts:
            print(f"- {row_id}: {detail}")
    if unresolved:
        print("\nStill unresolved:")
        for row_id in unresolved:
            print(f"- {row_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
