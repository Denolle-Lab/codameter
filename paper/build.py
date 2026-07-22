#!/usr/bin/env python3
"""Build the manuscript: Quarto markdown -> LaTeX -> PDF, one command.

The single editable source is the manuscript ``.qmd`` file in this directory
(currently ``manuscript_marine.qmd`` --- see :data:`SOURCE_CANDIDATES` if it is
ever renamed). This script

  1. (optionally) regenerates the synthetic-demo figures into ``literature/figs/``;
  2. regenerates the 103-study ``survey.bib`` and ``appendix_table.tex`` from the
     literature CSV (``paper/build_survey.py``);
  3. runs ``quarto render <source>.qmd --to pdf`` which, with ``keep-tex: true``,
     emits both ``<source>.tex`` (submission-ready LaTeX) and ``<source>.pdf``.

So you edit Markdown; you get TeX and PDF.

Usage::

    python paper/build.py              # regen survey table + render PDF (+TeX)
    python paper/build.py --figures    # also regenerate the demo figures first
    python paper/build.py --no-survey  # skip the survey/appendix regeneration
    python paper/build.py --qmd manuscript_marine.qmd  # pin the source explicitly
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# Preference order when --qmd is not given. The manuscript source has been
# renamed before (manuscript.qmd -> manuscript_marine.qmd); listing candidates
# here, instead of hardcoding one name, keeps a future rename from silently
# breaking the build the way it did last time ("No valid input files passed to
# render" with no indication of *which* file quarto expected).
SOURCE_CANDIDATES = ["manuscript_marine.qmd", "manuscript.qmd"]


def run(cmd: list[str], cwd: Path) -> None:
    print(f"$ {' '.join(cmd)}  (in {cwd})")
    subprocess.run(cmd, cwd=cwd, check=True)


def find_source(explicit: str | None) -> Path:
    if explicit:
        p = HERE / explicit
        if not p.exists():
            sys.exit(f"error: --qmd {explicit!r} not found in {HERE}")
        return p
    for name in SOURCE_CANDIDATES:
        p = HERE / name
        if p.exists():
            return p
    found = sorted(q.name for q in HERE.glob("*.qmd"))
    sys.exit(
        "error: no manuscript source found (looked for "
        f"{', '.join(SOURCE_CANDIDATES)} in {HERE}).\n"
        f"       .qmd files present: {found or '(none)'}\n"
        "       pass --qmd <file> to pin one explicitly."
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--figures",
        action="store_true",
        help="regenerate the synthetic-demo figures first",
    )
    ap.add_argument(
        "--no-survey",
        action="store_true",
        help="skip regenerating survey.bib + appendix_table.tex",
    )
    ap.add_argument(
        "--qmd", default=None, help="manuscript source filename (default: autodetect)"
    )
    args = ap.parse_args()

    if shutil.which("quarto") is None:
        sys.exit("error: 'quarto' not found on PATH (install from quarto.org).")

    source = find_source(args.qmd)
    print(f"manuscript source: {source.relative_to(ROOT)}")

    if args.figures:
        run([sys.executable, "literature/synthetic_dvv_demo.py"], ROOT)

    if not args.no_survey:
        run([sys.executable, "paper/build_survey.py"], ROOT)

    # Quarto reads/writes relative to the .qmd directory.
    run(["quarto", "render", source.name, "--to", "pdf"], HERE)

    pdf = source.with_suffix(".pdf")
    tex = source.with_suffix(".tex")
    print("\nBuild complete:")
    for p in (tex, pdf):
        print(f"  {'ok ' if p.exists() else 'MISSING '}{p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
