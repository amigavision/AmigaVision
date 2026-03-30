#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import html
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CURRENT_CSV = ROOT / "data/db/titles.csv"
OUTPUT_HTML = ROOT / "data/db/titles-changes-since-2025.05.05.html"
TAG = "2025.05.05"
ID_FIELD = "id"
TOKEN_RE = re.compile(r"\s+|[A-Za-z0-9]+|[^A-Za-z0-9\s]", re.UNICODE)
EXCLUDED_FIELDS = {
    "hol_id",
    "lemon_id",
    "pouet_id",
    "demozoo_id",
    "slave_version",
    "archive_path",
    "slave_path",
}


@dataclass
class DiffRow:
    status: str
    title: str
    diff_html: str


def read_csv_text(text: str) -> tuple[list[str], dict[str, dict[str, str]]]:
    reader = csv.DictReader(StringIO(text), delimiter=";")
    fieldnames = reader.fieldnames or []
    rows: dict[str, dict[str, str]] = {}
    for row in reader:
        row_id = row.get(ID_FIELD, "").strip()
        if not row_id:
            continue
        rows[row_id] = {field: (value or "") for field, value in row.items()}
    return fieldnames, rows


def load_current() -> tuple[list[str], dict[str, dict[str, str]]]:
    return read_csv_text(CURRENT_CSV.read_text(encoding="utf-8"))


def load_ref(ref: str) -> tuple[list[str], dict[str, dict[str, str]]]:
    result = subprocess.run(
        ["git", "show", f"{ref}:data/db/titles.csv"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return read_csv_text(result.stdout)


def tokenize(value: str) -> list[str]:
    if not value:
        return []
    return TOKEN_RE.findall(value)


def render_tokens(tokens: list[str]) -> str:
    return "".join(html.escape(token) for token in tokens)


def render_inline_diff(old: str, new: str) -> str:
    if old == new:
        return f'<span class="same">{html.escape(old) or "<empty>"}</span>'

    old_tokens = tokenize(old)
    new_tokens = tokenize(new)
    matcher = SequenceMatcher(a=old_tokens, b=new_tokens)
    parts: list[str] = []

    for opcode, a0, a1, b0, b1 in matcher.get_opcodes():
        if opcode == "equal":
            parts.append(render_tokens(new_tokens[b0:b1]))
        elif opcode == "delete":
            deleted = render_tokens(old_tokens[a0:a1]) or "&nbsp;"
            parts.append(f'<del class="diff-del">{deleted}</del>')
        elif opcode == "insert":
            inserted = render_tokens(new_tokens[b0:b1]) or "&nbsp;"
            parts.append(f'<ins class="diff-ins">{inserted}</ins>')
        elif opcode == "replace":
            deleted = render_tokens(old_tokens[a0:a1]) or "&nbsp;"
            inserted = render_tokens(new_tokens[b0:b1]) or "&nbsp;"
            parts.append(f'<del class="diff-del">{deleted}</del><ins class="diff-ins">{inserted}</ins>')

    return "".join(parts) or '<span class="same empty">&lt;empty&gt;</span>'


def display_value(value: str) -> str:
    return html.escape(value) if value else '<span class="empty">&lt;empty&gt;</span>'


def filter_row(row: dict[str, str] | None, ordered_fields: list[str]) -> dict[str, str]:
    if row is None:
        return {}
    return {field: row.get(field, "") for field in ordered_fields}


def build_field_diffs(
    status: str,
    old_row: dict[str, str] | None,
    new_row: dict[str, str] | None,
    ordered_fields: list[str],
) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []

    for field in ordered_fields:
        old_value = (old_row or {}).get(field, "")
        new_value = (new_row or {}).get(field, "")

        if status == "added":
            if not new_value:
                continue
            diff_html = f'<ins class="diff-ins">{display_value(new_value)}</ins>'
        elif status == "removed":
            if not old_value:
                continue
            diff_html = f'<del class="diff-del">{display_value(old_value)}</del>'
        else:
            if old_value == new_value:
                continue
            diff_html = render_inline_diff(old_value, new_value)

        items.append((field, diff_html))

    return items


def build_rows(base_ref: str) -> tuple[list[DiffRow], Counter[str]]:
    old_fields, old_rows = load_ref(base_ref)
    new_fields, new_rows = load_current()
    ordered_fields = [
        field
        for field in dict.fromkeys([*old_fields, *new_fields])
        if field not in EXCLUDED_FIELDS
    ]
    row_ids = sorted(set(old_rows) | set(new_rows))
    rows: list[DiffRow] = []
    counts: Counter[str] = Counter()

    status_order = {"modified": 0, "added": 1, "removed": 2}

    for row_id in row_ids:
        old_row = old_rows.get(row_id)
        new_row = new_rows.get(row_id)
        filtered_old_row = filter_row(old_row, ordered_fields) if old_row else None
        filtered_new_row = filter_row(new_row, ordered_fields) if new_row else None

        if old_row and not new_row:
            status = "removed"
            title_row = old_row
        elif new_row and not old_row:
            status = "added"
            title_row = new_row
        else:
            assert old_row is not None and new_row is not None
            if filtered_old_row == filtered_new_row:
                continue
            status = "modified"
            title_row = new_row

        counts[status] += 1
        title = title_row.get("title") or row_id
        for _field_name, diff_html in build_field_diffs(status, filtered_old_row, filtered_new_row, ordered_fields):
            rows.append(
                DiffRow(
                    status=status,
                    title=title,
                    diff_html=diff_html,
                )
            )

    rows.sort(
        key=lambda row: (
            status_order[row.status],
            row.title.casefold(),
            row.diff_html.casefold(),
        )
    )
    deduped_rows: list[DiffRow] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        key = (row.status, row.title, row.diff_html)
        if key in seen:
            continue
        seen.add(key)
        deduped_rows.append(row)
    return deduped_rows, counts


def render_html(rows: list[DiffRow], counts: Counter[str], base_ref: str) -> str:
    total = sum(counts.values())
    generated_from = html.escape(str(CURRENT_CSV.relative_to(ROOT)))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>titles.csv changes since {TAG}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f3eb;
      --panel: rgba(255, 255, 255, 0.9);
      --panel-strong: #fffdf8;
      --hero-bg: linear-gradient(135deg, rgba(255,255,255,0.92), rgba(255,248,235,0.92));
      --header-bg: rgba(255, 251, 243, 0.96);
      --row-hover-bg: rgba(255, 251, 243, 0.7);
      --pill-total-bg: #efe4d2;
      --pill-total-border: #dbc6aa;
      --text: #261d17;
      --muted: #75665a;
      --line: #d8cabb;
      --added: #176f3d;
      --added-bg: #dff5e6;
      --removed: #9d2438;
      --removed-bg: #fde1e5;
      --modified: #8a5a00;
      --modified-bg: #ffefc7;
      --shadow: 0 14px 40px rgba(63, 43, 24, 0.12);
    }}

    @media (prefers-color-scheme: dark) {{
      :root {{
        color-scheme: dark;
        --bg: #16120f;
        --panel: rgba(30, 24, 20, 0.92);
        --panel-strong: #211a15;
        --hero-bg: linear-gradient(135deg, rgba(41, 32, 26, 0.96), rgba(30, 24, 20, 0.96));
        --header-bg: rgba(40, 32, 26, 0.96);
        --row-hover-bg: rgba(53, 42, 34, 0.72);
        --pill-total-bg: rgba(78, 61, 46, 0.72);
        --pill-total-border: #6a5441;
        --text: #f3eadf;
        --muted: #bcae9f;
        --line: #4c3d31;
        --added: #8be0ad;
        --added-bg: rgba(24, 78, 49, 0.45);
        --removed: #ff9eac;
        --removed-bg: rgba(114, 33, 48, 0.45);
        --modified: #ffd37a;
        --modified-bg: rgba(116, 80, 15, 0.4);
        --shadow: 0 18px 46px rgba(0, 0, 0, 0.42);
      }}

      body {{
        background:
          radial-gradient(circle at top left, rgba(210, 148, 65, 0.12), transparent 26rem),
          linear-gradient(180deg, #1b1612 0%, var(--bg) 100%);
      }}
    }}

    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
      background:
        radial-gradient(circle at top left, rgba(192, 138, 63, 0.18), transparent 26rem),
        linear-gradient(180deg, #fbf7f0 0%, var(--bg) 100%);
      color: var(--text);
    }}

    .page {{
      width: min(1500px, calc(100vw - 32px));
      margin: 24px auto 40px;
    }}

    .hero {{
      background: var(--hero-bg);
      border: 1px solid rgba(134, 104, 68, 0.18);
      border-radius: 22px;
      box-shadow: var(--shadow);
      padding: 24px 26px;
      margin-bottom: 18px;
      backdrop-filter: blur(8px);
    }}

    h1 {{
      margin: 0 0 8px;
      font-size: clamp(2rem, 3vw, 3.2rem);
      line-height: 0.95;
      letter-spacing: -0.03em;
    }}

    .lede {{
      margin: 0;
      color: var(--muted);
      font-size: 1.03rem;
      max-width: 72ch;
    }}

    .summary {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 18px;
    }}

    .pill {{
      border-radius: 999px;
      padding: 8px 12px;
      font: 600 0.95rem/1.1 "Avenir Next", "Segoe UI", sans-serif;
      border: 1px solid transparent;
    }}

    .pill strong {{
      font-size: 1.05rem;
      margin-right: 6px;
    }}

    .pill-total {{
      background: var(--pill-total-bg);
      border-color: var(--pill-total-border);
    }}

    .pill-modified {{
      background: var(--modified-bg);
      color: #6d4700;
      border-color: #f0d48f;
    }}

    .pill-added {{
      background: var(--added-bg);
      color: #125c33;
      border-color: #bbdfc6;
    }}

    .pill-removed {{
      background: var(--removed-bg);
      color: #852134;
      border-color: #efbec7;
    }}

    .table-wrap {{
      overflow: auto;
      background: var(--panel);
      border-radius: 22px;
      border: 1px solid rgba(134, 104, 68, 0.18);
      box-shadow: var(--shadow);
      backdrop-filter: blur(8px);
    }}

    table {{
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;
      min-width: 980px;
    }}

    thead th {{
      position: sticky;
      top: 0;
      z-index: 1;
      text-align: left;
      font: 700 0.86rem/1.2 "Avenir Next", "Segoe UI", sans-serif;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      background: var(--header-bg);
      border-bottom: 1px solid var(--line);
      padding: 14px 16px;
    }}

    tbody td {{
      vertical-align: top;
      padding: 8px 10px;
      border-bottom: 1px solid rgba(216, 202, 187, 0.85);
    }}

    tbody tr:hover {{
      background: var(--row-hover-bg);
    }}

    .status {{
      width: 92px;
    }}

    .status-badge {{
      display: inline-block;
      min-width: 82px;
      text-align: center;
      border-radius: 999px;
      padding: 7px 10px;
      font: 700 0.78rem/1 "Avenir Next", "Segoe UI", sans-serif;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    .status-modified {{ background: var(--modified-bg); color: #724900; }}
    .status-added {{ background: var(--added-bg); color: var(--added); }}
    .status-removed {{ background: var(--removed-bg); color: var(--removed); }}

    .title-cell {{
      min-width: 260px;
    }}

    .title-main {{
      font-size: 0.97rem;
      font-weight: 700;
      margin-bottom: 2px;
    }}

    .diff-col {{
      min-width: 460px;
      font-size: 0.9rem;
      line-height: 1.35;
      word-break: break-word;
    }}

    ins, del {{
      text-decoration-thickness: 2px;
      padding: 0 0.12em;
      border-radius: 0.3em;
    }}

    .diff-ins {{
      color: var(--added);
      background: var(--added-bg);
      text-decoration: none;
    }}

    .diff-del {{
      color: var(--removed);
      background: var(--removed-bg);
      text-decoration: line-through;
    }}

    .empty {{
      color: #9a8a7d;
      font-style: italic;
    }}

    .same {{
      color: var(--text);
    }}

    @media (max-width: 900px) {{
      .page {{
        width: min(100vw - 16px, 100%);
        margin: 8px auto 24px;
      }}

      .hero {{
        border-radius: 18px;
        padding: 18px;
      }}

      tbody td, thead th {{
        padding: 8px;
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <h1>Changes in <code>{generated_from}</code></h1>
      <p class="lede">Compared against git ref <code>{html.escape(base_ref)}</code>. Each changed field gets its own compact table row, with inline diffs for fast scanning.</p>
      <div class="summary">
        <div class="pill pill-total"><strong>{total}</strong> changed titles</div>
        <div class="pill pill-total"><strong>{len(rows)}</strong> changed fields</div>
        <div class="pill pill-modified"><strong>{counts["modified"]}</strong> modified</div>
        <div class="pill pill-added"><strong>{counts["added"]}</strong> added</div>
        <div class="pill pill-removed"><strong>{counts["removed"]}</strong> removed</div>
      </div>
    </section>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Status</th>
            <th>Title</th>
            <th>Diff</th>
          </tr>
        </thead>
        <tbody>
          {"".join(render_row(row) for row in rows)}
        </tbody>
      </table>
    </div>
  </div>
</body>
</html>
"""


def render_row(row: DiffRow) -> str:
    return (
        "<tr>"
        f'<td class="status"><span class="status-badge status-{row.status}">{html.escape(row.status)}</span></td>'
        '<td class="title-cell">'
        f'<div class="title-main">{html.escape(row.title)}</div>'
        "</td>"
        f'<td class="diff-col">{row.diff_html}</td>'
        "</tr>"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an HTML report of titles.csv changes versus a git ref.")
    parser.add_argument("--base-ref", default=TAG, help="Git ref to compare the current working tree against.")
    parser.add_argument("--output", default=str(OUTPUT_HTML), help="Output HTML file path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_html = Path(args.output).expanduser()
    if not output_html.is_absolute():
        output_html = (ROOT / output_html).resolve()
    rows, counts = build_rows(args.base_ref)
    output_html.write_text(render_html(rows, counts, args.base_ref), encoding="utf-8")
    print(
        f"Wrote {output_html.relative_to(ROOT)} with "
        f"{sum(counts.values())} changed titles and {len(rows)} changed fields."
    )


if __name__ == "__main__":
    main()
