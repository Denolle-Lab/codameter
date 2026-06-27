#!/usr/bin/env python3
"""Generate the synthetic dv/v "processing-choice" figures for the survey.

Each of the seven figures imposes a *known* ground-truth dv/v(t), builds noisy
daily CCFs (see :mod:`codameter.synthetic_demo`), and recovers dv/v under
different processing choices — including deliberate deviations from best
practice (wrong estimator, fixed window across bands, moving reference, clock
error, seasonal late-coda noise) — so every gap between the recovered curve and
the black truth is an artefact of a decision, not of nature.

The figure builders live in :mod:`codameter.synthetic_demo` so this CLI and the
Quarto narrative page (`quarto/survey-synthetic-demo.qmd`) share one source of
truth. Outputs (PNG) land in literature/figs/. Run:

    pixi run python literature/synthetic_dvv_demo.py
"""
from pathlib import Path

from codameter.synthetic_demo import build_all

if __name__ == "__main__":
    build_all(Path(__file__).resolve().parent / "figs")
    print("\nDone.")
