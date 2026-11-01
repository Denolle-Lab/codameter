# Context pack for iteration-2 subagents (reconciliation mode)

Manuscript: "The reproducibility cost of ad-hoc processing choices in ambient-noise seismic velocity-change monitoring" (M. A. Denolle). Target: GJI, research paper with methods emphasis. Author profile: default (`/Users/marinedenolle/.claude/skills/pre-submission-reviewer/profiles/default.md`). Repository: /Users/marinedenolle/GitHub/codameter.

GJI calibration row: solid solid-Earth contribution; science first, grammar deferred to copyediting unless it impedes review; RAS Editorial Code of Practice for data and code; summary is one paragraph, at most 500 words for a research paper.

## What to read
- Current manuscript: `paper/manuscript_marine.qmd` (Quarto markdown with raw LaTeX tables and figure environments). Rendered PDF: `paper/manuscript_marine.pdf` (80 pages; the Read tool renders pages on request).
- Reviewed version (iteration 1, commit b6dbbd0): `/private/tmp/claude-501/-Users-marinedenolle-GitHub-codameter/6375a335-563a-4b77-a1d2-2226191cc2a0/scratchpad/ms_before.qmd`.
- Unified diff between them: `reviews/codameter-gji.iter2.diff`. Section-level change map: `reviews/codameter-gji.changes.json`.
- Iteration-1 review reports (context for the prior findings): `review/README.md`, `review/01_manuscript_and_figures.md`, `review/02_software_and_uncertainty.md`, `review/03_advisor_and_golden_dataset.md`, and `review/evidence/` (probes, per-section notes).
- Closure evidence produced during the revision: `review/evidence/closure/README.md` and the JSON probe outputs there; `review/EXECUTION_PLAN.md` (what was changed and why, with a dated log). Treat these as the author's claims, not as proof: verify against the manuscript text and the code.
- Figures with numerical sidecars: `literature/figs/<name>.png`, `.npz`, `.json`; `literature/figs/SOURCES.md`.
- Code: `src/codameter/` (uq_measurement.py, uq_processing.py, uq_bayes.py, calibration.py, golden.py, frugalmind.py, figures.py, deviations.py, inverse/linear_fit.py, bench.py); tests in `tests/`. Field comparison: `scripts/compare_gate1.py`, `paper/data/gate1/comparison.json`, `paper/data/gate1/README.md`. Calibration runs: `paper/data/calibration/*.json`, table `paper/calibration_table.tex`.
- You may run commands (pytest, python) from the repository root with `.pixi/envs/dev/bin/python`; set `MPLCONFIGDIR=/tmp/mpl`.

## Disclosure
The revision was drafted by an AI agent (Claude) under the author's direction; the orchestrator of this review is the same agent lineage. Your independence is the safeguard: do not defer to the execution plan's account of what was fixed. Check.

## Reconciliation rules (skill v2.5, iteration N>=2)
1. For every prior finding in your scope file, assign exactly one verdict: RESOLVED / PARTIALLY ADDRESSED / NOT ADDRESSED / REGRESSED. Cite the changed text (quote a phrase and give its current line number, or a code path) that justifies RESOLVED or REGRESSED. A C2/C3/C4 finding is RESOLVED only when changed text or code demonstrably fixes it, never because the plan says so.
2. Raise a new finding only on changed spans (see the diff), in a separate bucket named INTRODUCED-IN-REVISION, each with location and tier. Do not re-scan unchanged text for new issues.
3. Many one-to-four-line "changes" in the diff are the replacement of `~\ref` by `\ \ref` (a typesetting fix for literal tildes) or the joining of a line ending in `\dvv\`. These are not content changes; do not raise findings on them.
4. Monotonicity: do not move a finding to a worse tier than iteration 1 unless the change is tied to changed text.
5. Voice: the default profile applies; flag clarity and correctness, never register or word choice (S-PR alone may flag register, from its lexicon only).
6. Be specific: every finding cites a section, line, figure or code path, and states the fix.

## Output block (uniform)
```
SUBAGENT <ID>  scope: <...>  changed-scope re-dispatch: yes/no
INVENTORY: <what you read; counts where the reference file asks for them>
RECONCILIATION:
<PRIOR-ID> | <verdict> | <evidence: quoted phrase + current line, or code path> | <what remains, if any>
...
INTRODUCED-IN-REVISION (only on changed spans):
<ID>.N | <tier> | <location> | <finding> | <fix>
...
TIER FEED: <criterion>: <tier> (one line per criterion you serve, with one-sentence justification)
TOP FIXES: <ordered, at most five>
```
