#!/usr/bin/env python3
"""Merge the per-application dv/v literature scans into shareable tables.

Reads literature/raw/*.json (one array of paper rows per application group),
deduplicates by DOI (a few foundational papers legitimately appear in several
groups), and writes:

  - dvv_processing_parameters.csv   machine-readable master table
  - dvv_processing_parameters.md    rendered table, grouped by application, with
                                    clickable DOI links

Run:  python literature/build_table.py
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"

# Display order for the application groups.
APP_ORDER = [
    "Volcano",
    "Earthquake/Fault",
    "Landslide",
    "Groundwater/Hydrology",
    "Cryosphere",
    "Geothermal/Reservoir",
    "Methodology",
]

# Column order for the CSV (also defines the schema shared with colleagues).
COLUMNS = [
    "application",
    "authors_year",
    "year",
    "target_process",
    "region_site",
    "signal_source",
    "components",
    "freq_band_hz",
    "coda_window_s",
    "dvv_method",
    "stack_scheme",
    "station_config",
    "depth_sensitivity",
    "dvv_amplitude",
    "uncertainty_treatment",
    "best_practice_note",
    "also_applications",
    "doi_url",
    "open_access_format",
]


def norm_doi(url: str) -> str:
    """Normalize a DOI/URL so the same paper from two groups collapses to one key."""
    u = (url or "").strip().lower()
    m = re.search(r"10\.\d{4,9}/[^\s\"<>]+", u)
    if m:
        return m.group(0).rstrip(".")
    return u  # non-DOI URLs (e.g. ADS abstract) fall back to the raw url


def nr_count(row: dict) -> int:
    """How many schema fields are 'n/r' / 'n/a' — used to keep the richest copy."""
    return sum(
        1
        for c in COLUMNS
        if c not in ("also_applications",)
        and str(row.get(c, "")).strip().lower() in ("n/r", "n/a", "")
    )


def load_rows() -> list[dict]:
    rows: list[dict] = []
    for path in sorted(RAW.glob("*.json")):
        if path.name.startswith("."):  # skip caches / hidden files
            continue
        with path.open() as fh:
            for row in json.load(fh):
                row.setdefault("also_applications", "")
                rows.append(row)
    return rows


def merge(rows: list[dict]) -> list[dict]:
    """Deduplicate by DOI, preferring the row with the most populated fields.

    The primary (kept) row's `application` wins; the other groups it appeared in
    are recorded in `also_applications` so cross-cutting papers stay traceable.
    """
    by_doi: dict[str, dict] = {}
    apps_seen: dict[str, list[str]] = {}
    for row in rows:
        key = norm_doi(row["doi_url"])
        apps_seen.setdefault(key, [])
        if row["application"] not in apps_seen[key]:
            apps_seen[key].append(row["application"])
        if key not in by_doi or nr_count(row) < nr_count(by_doi[key]):
            by_doi[key] = row

    merged = []
    for key, row in by_doi.items():
        primary = row["application"]
        others = [a for a in apps_seen[key] if a != primary]
        row = dict(row)
        row["also_applications"] = "; ".join(others)
        merged.append(row)

    def sort_key(r: dict):
        app = r["application"]
        app_rank = APP_ORDER.index(app) if app in APP_ORDER else len(APP_ORDER)
        return (app_rank, r.get("year", ""), r.get("authors_year", ""))

    return sorted(merged, key=sort_key)


def write_csv(rows: list[dict]) -> None:
    out = HERE / "dvv_processing_parameters.csv"
    with out.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in COLUMNS})
    print(f"wrote {out}  ({len(rows)} unique papers)")


# Compact columns rendered in the Markdown table (full detail lives in the CSV).
MD_COLS = [
    ("authors_year", "Study"),
    ("region_site", "Site / region"),
    ("target_process", "Target process"),
    ("signal_source", "Source"),
    ("freq_band_hz", "Freq (Hz)"),
    ("coda_window_s", "Coda (s)"),
    ("dvv_method", "Method"),
    ("station_config", "Geometry"),
    ("depth_sensitivity", "Depth sensitivity"),
    ("dvv_amplitude", "Typical dv/v"),
]


def md_cell(text: str) -> str:
    return str(text or "").replace("|", "\\|").replace("\n", " ").strip()


def write_markdown(rows: list[dict]) -> None:
    out = HERE / "dvv_processing_parameters.md"
    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(row["application"], []).append(row)

    fmt_count = {}
    for row in rows:
        fmt_count[row["open_access_format"]] = fmt_count.get(row["open_access_format"], 0) + 1

    lines: list[str] = []
    lines.append("# dv/v passive-monitoring processing parameters by application")
    lines.append("")
    lines.append(
        f"Literature-derived processing parameters for ambient-noise / coda "
        f"seismic velocity-change (dv/v) monitoring, organized by science "
        f"application. **{len(rows)} unique studies.** Every row links to a "
        f"verified DOI; `n/r` = not reported in the source (not guessed)."
    )
    lines.append("")
    lines.append(
        "The machine-readable version with all columns is "
        "[dvv_processing_parameters.csv](dvv_processing_parameters.csv); "
        "consolidated best-practice rules are in "
        "[best_practices.md](best_practices.md); column definitions and "
        "methodology are in [README.md](README.md)."
    )
    lines.append("")

    # Per-application counts.
    lines.append("| Application | Studies |")
    lines.append("| --- | --- |")
    for app in APP_ORDER:
        if app in groups:
            lines.append(f"| {app} | {len(groups[app])} |")
    lines.append(f"| **Total (unique)** | **{len(rows)}** |")
    lines.append("")

    header = "| " + " | ".join(label for _, label in MD_COLS) + " | Link |"
    divider = "| " + " | ".join("---" for _ in MD_COLS) + " | --- |"

    for app in APP_ORDER:
        if app not in groups:
            continue
        lines.append(f"## {app}")
        lines.append("")
        lines.append(header)
        lines.append(divider)
        for row in groups[app]:
            cells = [md_cell(row.get(col, "")) for col, _ in MD_COLS]
            also = row.get("also_applications", "")
            study = cells[0] + (f" †" if also else "")
            cells[0] = study
            fmt = row.get("open_access_format", "")
            link = f"[DOI]({row['doi_url']}) ({fmt})"
            lines.append("| " + " | ".join(cells) + f" | {link} |")
        # Footnote about cross-application papers in this group.
        cross = [r for r in groups[app] if r.get("also_applications")]
        if cross:
            notes = "; ".join(
                f"{md_cell(r['authors_year'])} → also {r['also_applications']}"
                for r in cross
            )
            lines.append("")
            lines.append(f"† Cross-application study: {notes}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "**Access formats:** "
        + ", ".join(f"{k}: {v}" for k, v in sorted(fmt_count.items()))
        + ". Paywalled rows have more `n/r` cells because internal parameters "
        "could not be verified from the abstract alone."
    )
    lines.append("")

    out.write_text("\n".join(lines))
    print(f"wrote {out}")


def main() -> None:
    rows = load_rows()
    merged = merge(rows)
    print(f"loaded {len(rows)} rows -> {len(merged)} unique papers")
    write_csv(merged)
    write_markdown(merged)


if __name__ == "__main__":
    main()
