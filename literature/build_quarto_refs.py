#!/usr/bin/env python3
"""Build the Quarto references page from the dv/v survey CSV.

Enriches each DOI via the Crossref REST API (title, authors, journal, year),
caches the responses, and writes ../quarto/survey-references.qmd — a full
reference list with clickable DOI/URL links, grouped by application.

Run:  python literature/build_quarto_refs.py
"""
from __future__ import annotations

import csv
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSV = HERE / "dvv_processing_parameters.csv"
CACHE = HERE / ".crossref_cache.json"
OUT = HERE.parent / "quarto" / "survey-references.qmd"
MAILTO = "mdenolle@uw.edu"

APP_ORDER = [
    "Volcano", "Earthquake/Fault", "Landslide", "Groundwater/Hydrology",
    "Cryosphere", "Geothermal/Reservoir", "Methodology",
]


def doi_of(url: str) -> str | None:
    m = re.search(r"10\.\d{4,9}/[^\s\"<>]+", (url or "").lower())
    return m.group(0).rstrip(".") if m else None


def load_cache() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text())
    return {}


def fetch_crossref(doi: str, cache: dict) -> dict | None:
    if doi in cache:
        return cache[doi]
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}?mailto={MAILTO}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": f"codameter/1.0 (mailto:{MAILTO})"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            msg = json.load(resp)["message"]
    except Exception as exc:  # noqa: BLE001
        print(f"  crossref miss {doi}: {exc}")
        cache[doi] = None
        return None
    rec = {
        "title": (msg.get("title") or [""])[0],
        "container": (msg.get("container-title") or [""])[0],
        "year": str((msg.get("issued", {}).get("date-parts", [[None]])[0] or [None])[0] or ""),
        "authors": [
            {"family": a.get("family", ""), "given": a.get("given", "")}
            for a in msg.get("author", [])
        ],
        "volume": msg.get("volume", ""),
        "page": msg.get("page", ""),
    }
    cache[doi] = rec
    time.sleep(0.15)  # be polite to Crossref
    return rec


def fmt_authors(authors: list[dict]) -> str:
    def one(a: dict) -> str:
        fam = a.get("family", "").strip()
        giv = a.get("given", "").strip()
        initials = " ".join(f"{p[0]}." for p in re.split(r"[\s\-]+", giv) if p)
        return f"{fam}, {initials}".strip().rstrip(",") if fam else ""

    names = [one(a) for a in authors if a.get("family")]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) <= 8:
        return ", ".join(names[:-1]) + f", & {names[-1]}"
    return ", ".join(names[:8]) + ", et al."


def surname(authors_year: str) -> str:
    head = re.split(r"[,(&]", authors_year.strip())[0]
    return head.strip().lower()


def full_citation(row: dict, rec: dict | None) -> str:
    """Prefer Crossref metadata; fall back to the CSV's authors_year string."""
    year = row.get("year", "")
    if rec and rec.get("title"):
        authors = fmt_authors(rec["authors"]) or row["authors_year"]
        yr = rec.get("year") or year
        title = rec["title"].rstrip(". ")
        journal = rec.get("container", "")
        vol = rec.get("volume", "")
        bits = [f"{authors} ({yr}). {title}."]
        if journal:
            jb = f"*{journal}*"
            if vol:
                jb += f", {vol}"
            bits.append(jb + ".")
        return " ".join(bits)
    # Fallback: no Crossref record.
    return f"{row['authors_year']}. ({year})."


def main() -> None:
    rows = list(csv.DictReader(CSV.open()))
    cache = load_cache()
    enriched = []
    for i, row in enumerate(rows, 1):
        doi = doi_of(row["doi_url"])
        rec = fetch_crossref(doi, cache) if doi else None
        enriched.append((row, rec))
        if i % 20 == 0:
            print(f"  {i}/{len(rows)} enriched")
    CACHE.write_text(json.dumps(cache, indent=0))

    # Sort alphabetically by first-author surname, then year.
    enriched.sort(key=lambda er: (surname(er[0]["authors_year"]), er[0].get("year", "")))

    have = sum(1 for _, rec in enriched if rec and rec.get("title"))
    lines: list[str] = []
    lines.append("---")
    lines.append('title: "dv/v monitoring literature — references"')
    lines.append('subtitle: "Full citations for the processing-parameter survey, with DOI & links"')
    lines.append("toc: true")
    lines.append("toc-depth: 2")
    lines.append("---")
    lines.append("")
    lines.append(
        f"Full citations for the **{len(rows)} studies** in the "
        "[processing-parameter survey](survey-best-practices.qmd). "
        f"{have} enriched with title/journal metadata via "
        "[Crossref](https://www.crossref.org); the remainder show the short "
        "citation. Each entry links to its DOI (or source URL)."
    )
    lines.append("")
    lines.append(
        "The full per-study parameter table (CSV + Markdown) lives in "
        "[`literature/`](https://github.com/Denolle-Lab/codameter/tree/master/literature) "
        "in the repository."
    )
    lines.append("")

    # --- Alphabetical master list ---
    lines.append("## All studies (alphabetical)")
    lines.append("")
    for row, rec in enriched:
        cite = full_citation(row, rec)
        apps = row["application"]
        if row.get("also_applications"):
            apps += "; " + row["also_applications"]
        url = row["doi_url"]
        link = f"[{url.replace('https://', '')}]({url})"
        lines.append(f"- {cite} {link} ‹{apps}›")
    lines.append("")

    # --- Grouped by application ---
    lines.append("## By application")
    lines.append("")
    for app in APP_ORDER:
        group = [
            (row, rec) for row, rec in enriched
            if row["application"] == app or app in (row.get("also_applications", "").split("; "))
        ]
        if not group:
            continue
        lines.append(f"### {app} ({len(group)})")
        lines.append("")
        for row, rec in sorted(group, key=lambda er: (surname(er[0]["authors_year"]), er[0].get("year", ""))):
            cite = full_citation(row, rec)
            url = row["doi_url"]
            link = f"[DOI / source]({url})"
            lines.append(f"- {cite} {link}")
        lines.append("")

    OUT.write_text("\n".join(lines))
    print(f"wrote {OUT}  ({len(rows)} refs, {have} Crossref-enriched)")


if __name__ == "__main__":
    main()
