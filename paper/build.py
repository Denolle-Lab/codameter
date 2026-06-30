#!/usr/bin/env python3
"""Build the manuscript: Quarto markdown -> LaTeX -> PDF, one command.

The single editable source is ``paper/manuscript.qmd``. This script

  1. (optionally) regenerates the synthetic-demo figures into ``literature/figs/``;
  2. regenerates the 103-study ``survey.bib`` and ``appendix_table.tex`` from the
     literature CSV (``paper/build_survey.py``);
  3. runs ``quarto render manuscript.qmd --to pdf`` which, with ``keep-tex: true``,
     emits both ``manuscript.tex`` (submission-ready LaTeX) and ``manuscript.pdf``.

So you edit Markdown; you get TeX and PDF.

Usage::

    python paper/build.py              # regen survey table + render PDF (+TeX)
    python paper/build.py --figures    # also regenerate the demo figures first
    python paper/build.py --no-survey  # skip the survey/appendix regeneration
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def run(cmd: list[str], cwd: Path) -> None:
    print(f"$ {' '.join(cmd)}  (in {cwd})")
    subprocess.run(cmd, cwd=cwd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--figures", action="store_true",
                    help="regenerate the synthetic-demo figures first")
    ap.add_argument("--no-survey", action="store_true",
                    help="skip regenerating survey.bib + appendix_table.tex")
    args = ap.parse_args()

    if shutil.which("quarto") is None:
        sys.exit("error: 'quarto' not found on PATH (install from quarto.org).")

    if args.figures:
        run([sys.executable, "literature/synthetic_dvv_demo.py"], ROOT)

    if not args.no_survey:
        run([sys.executable, "paper/build_survey.py"], ROOT)

    # Quarto reads/writes relative to the .qmd directory.
    run(["quarto", "render", "manuscript.qmd", "--to", "pdf"], HERE)

    pdf = HERE / "manuscript.pdf"
    tex = HERE / "manuscript.tex"
    print("\nBuild complete:")
    for p in (tex, pdf):
        print(f"  {'ok ' if p.exists() else 'MISSING '}{p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
