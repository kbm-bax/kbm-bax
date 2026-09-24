#!/usr/bin/env python3
"""Render assets/activity.svg from public GitHub contribution and language data."""

from __future__ import annotations

import json
import urllib.request
from datetime import date
from pathlib import Path

USER = "kbm-bax"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "activity.svg"

LEVELS = {
    0: "#1a2233",
    1: "#4a3b2c",
    2: "#8a6842",
    3: "#d4a574",
    4: "#f3d7b0",
}
LANG_COLOR = {
    "Python": "#e7c79a",
    "C#": "#f6f1e7",
    "Shell": "#8d877c",
    "TypeScript": "#c9956a",
    "Jupyter Notebook": "#6e7c99",
}
LANG_LABEL = {
    "Jupyter Notebook": "Notebook",
}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
FONT = "'JetBrains Mono', ui-monospace, Menlo, Consolas, monospace"


def fetch_json(url: str) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": "kbm-bax-profile"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def shares(counts: dict[str, int]) -> list[tuple[str, int]]:
    total = sum(counts.values())
    raw = [(name, counts[name] * 100 / total) for name in counts]
    floors = [(name, int(value)) for name, value in raw]
    leftover = 100 - sum(value for _, value in floors)
    order = sorted(range(len(raw)), key=lambda i: raw[i][1] - floors[i][1], reverse=True)
    pct = {name: value for name, value in floors}
    for i in order[:leftover]:
        pct[raw[i][0]] += 1
    return [(name, pct[name]) for name in counts]


def month_labels(weeks: list[list]) -> list[tuple[int, str]]:
    labels: list[tuple[int, str]] = []
    seen: set[int] = set()
    for i, week in enumerate(weeks):
        for item in week:
            if item is None:
                continue
            month = item[0].month
            if month in seen:
                break
            seen.add(month)
            if labels and i - labels[-1][0] < 2:
                labels[-1] = (i, MONTHS[month - 1])
            else:
                labels.append((i, MONTHS[month - 1]))
            break
    return labels


def render() -> str:
    payload = fetch_json(f"https://github-contributions-api.jogruber.de/v4/{USER}?y=last")
    days = [
        (date.fromisoformat(item["date"]), int(item["level"]), int(item["count"]))
        for item in payload["contributions"]
    ]
    total = int(payload["total"]["lastYear"])

    lead = (days[0][0].weekday() + 1) % 7
    cells: list = [None] * lead + days
    cols = (len(cells) + 6) // 7
    cells.extend([None] * (cols * 7 - len(cells)))
    weeks = [cells[i * 7 : (i + 1) * 7] for i in range(cols)]

    repos = fetch_json(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner")
    counts: dict[str, int] = {}
    for repo in repos:
        if repo.get("fork"):
            continue
        languages = fetch_json(repo["languages_url"])
        for name, nbytes in languages.items():
            counts[name] = counts.get(name, 0) + int(nbytes)
    top = dict(sorted(counts.items(), key=lambda item: item[1], reverse=True)[:5])
    mix = shares(top)

    cell = 15
    gap = 4
    step = cell + gap
    left = 48
    top = 86
    width = left + cols * step + 36
    bar_y = top + 7 * step + 46
    height = bar_y + 58

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{total} public contributions in the last year">',
        f'  <rect width="{width}" height="{height}" rx="16" fill="#070b14" stroke="#243049" stroke-width="1.5"/>',
        f'  <text x="48" y="40" fill="#d4a574" font-family="{FONT}" font-size="13" letter-spacing="3">LAST YEAR</text>',
        f'  <text x="{width - 48}" y="42" fill="#f6f1e7" font-family="{FONT}" font-size="16" text-anchor="end">{total} contributions</text>',
    ]
    for index, label in month_labels(weeks):
        lines.append(
            f'  <text x="{left + index * step}" y="68" fill="#8d877c" font-family="{FONT}" font-size="11">{label}</text>'
        )
    for col, week in enumerate(weeks):
        for row, item in enumerate(week):
            if item is None:
                continue
            day, level, count = item
            fill = LEVELS.get(level, LEVELS[0])
            x = left + col * step
            y = top + row * step
            lines.append(
                f'  <rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{fill}"><title>{day.isoformat()}: {count}</title></rect>'
            )

    legend_x = width - 48 - (5 * 16 + 78)
    legend_y = top + 7 * step + 6
    lines.append(
        f'  <text x="{legend_x - 8}" y="{legend_y + 11}" fill="#8d877c" font-family="{FONT}" font-size="11" text-anchor="end">less</text>'
    )
    for level in range(5):
        lines.append(
            f'  <rect x="{legend_x + level * 16}" y="{legend_y}" width="12" height="12" rx="2" fill="{LEVELS[level]}"/>'
        )
    lines.append(
        f'  <text x="{legend_x + 5 * 16 + 4}" y="{legend_y + 11}" fill="#8d877c" font-family="{FONT}" font-size="11">more</text>'
    )

    lines.append(
        f'  <text x="48" y="{bar_y}" fill="#d4a574" font-family="{FONT}" font-size="13" letter-spacing="3">PUBLIC CODE</text>'
    )
    bar_w = width - 96
    cursor = 48
    bar_top = bar_y + 14
    for index, (name, pct) in enumerate(mix):
        segment = round(bar_w * pct / 100)
        if index == len(mix) - 1:
            segment = 48 + bar_w - cursor
        lines.append(
            f'  <rect x="{cursor}" y="{bar_top}" width="{segment}" height="10" fill="{LANG_COLOR.get(name, "#8d877c")}"/>'
        )
        cursor += segment

    cursor = 48
    label_y = bar_top + 32
    for name, pct in mix:
        label = f"{LANG_LABEL.get(name, name)} {pct}%"
        lines.append(
            f'  <rect x="{cursor}" y="{label_y - 9}" width="8" height="8" rx="2" fill="{LANG_COLOR.get(name, "#8d877c")}"/>'
        )
        lines.append(
            f'  <text x="{cursor + 14}" y="{label_y}" fill="#c8c2b4" font-family="{FONT}" font-size="12">{label}</text>'
        )
        cursor += 28 + len(label) * 8
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def main() -> None:
    svg = render()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists() and OUT.read_text() == svg:
        print("activity.svg unchanged")
        return
    OUT.write_text(svg)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
