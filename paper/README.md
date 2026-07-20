# Short paper draft (GJI)

Draft manuscript: **"The reproducibility cost of ad-hoc processing choices in
ambient-noise seismic velocity-change monitoring."**

A short *Geophysical Journal International* paper built on the
[`literature/`](../literature) survey and the executable
[`codameter.synthetic_demo`](../src/codameter/synthetic_demo.py) framework.

## GJI submission format

The manuscript is prepared for a GJI **initial submission** (set in
[`_preamble.tex`](_preamble.tex)):

- the abstract is labelled **SUMMARY** and is ≤ 250 words;
- a **Key words** line (from the GJI controlled list) follows the summary;
- text is **double-spaced** with continuous **line numbers** (tables kept
  single-spaced; the `lineno` patch keeps amsmath display equations intact);
- a **Data Availability** statement and Acknowledgements are included;
- references are author–year (`natbib`), close to GJI house style.

For production/acceptance, the emitted **`manuscript_marine.tex`** can be
dropped into the official **`gji.cls`** template (from the GJI author
resources) and the reference style switched to `gji.bst`; the content is
already structured for it. Co-authors, author contributions, and a
competing-interests statement remain to be filled before submission.

## Edit in Markdown, get TeX + PDF

The **single editable source is [`manuscript_marine.qmd`](manuscript_marine.qmd)**
(Quarto Markdown). You never edit LaTeX by hand. One command renders it:

```
pixi run python paper/build.py
```

Run it from the repo root, inside the `pixi` environment (not a bare
`python paper/build.py` — that uses whatever Python is first on your `PATH`,
which may lack the packages the survey/figure regeneration steps need).

This:
1. regenerates [`survey.bib`](survey.bib) + [`appendix_table.tex`](appendix_table.tex)
   from the literature CSV (`build_survey.py`), and
2. runs `quarto render manuscript_marine.qmd --to pdf`, which (with `keep-tex: true`)
   emits both **`manuscript_marine.tex`** (submission-ready LaTeX) and
   **`manuscript_marine.pdf`**.

So: **`manuscript_marine.qmd` → `manuscript_marine.tex` → `manuscript_marine.pdf`.**
The `.tex` is a *generated* artifact — do not edit it by hand.

`build.py` autodetects the source filename (see `SOURCE_CANDIDATES` in
`build.py`) rather than hardcoding it, so a future rename doesn't silently
break the build the way it did once already (see *Troubleshooting* below). Pin
it explicitly with `--qmd` if you ever have more than one `.qmd` in this
directory:
```
pixi run python paper/build.py --qmd manuscript_marine.qmd
```

Options:
```
pixi run python paper/build.py --figures     # also regenerate the demo figures first
pixi run python paper/build.py --no-survey   # skip regenerating the survey table/bib
```

### Prerequisites
- [Quarto](https://quarto.org) on `PATH` (`quarto --version`).
- A LaTeX engine `quarto` can drive (`lualatex` + `bibtex`); this repo has been
  built against TeX Live 2018. Missing packages surface as a `quarto render`
  failure with a LaTeX log reference — read the log named after the source
  file (e.g. `manuscript_marine.log`), not just the truncated stdout.
- The `pixi` environment installed (`pixi install` once, from the repo root).

### Troubleshooting
- **`ERROR: No valid input files passed to render`** — `quarto` was pointed at
  a `.qmd` filename that no longer exists in `paper/`. This happens if the
  manuscript source gets renamed (it has, once: `manuscript.qmd` →
  `manuscript_marine.qmd`) without updating whatever calls `quarto render`
  directly. `build.py` now autodetects the source (see above), so this should
  not recur through `build.py`; it can still happen if you call
  `quarto render <name>.qmd` by hand with a stale name.
- **A YAML error citing the `author:`/`affiliations:` block** — the front
  matter's indentation broke (a list item was likely inserted at the wrong
  indent level, or a key ended up nested inside a list it isn't part of).
  Quarto's error message gives the exact line; fix the indentation so
  `affiliations:` is a list of `- name: ...` entries and top-level keys
  (`date:`, `abstract:`, …) sit back at zero indent, not inside that list.
- **LaTeX `Undefined control sequence` on a `\V`, `\dvv`-like token, or similar**
  — almost always a missing character in inline math, e.g. `$\Delta
  V_S(z)\V_S(z)$` instead of `$\Delta V_S(z)/V_S(z)$` (a dropped `/`). The
  `quarto render` output prints the exact `.qmd` line number under
  `Undefined control sequence` — go straight there.
- **BibTeX: `I was expecting a` {` or a` (` ---line N of file references.bib`,
  followed by unrelated citations silently going missing** — a `%` comment in
  a `.bib` file contains a literal `@` character (e.g. writing `@misc` in
  prose to *describe* a fallback entry type). BibTeX has no true line-comment
  syntax: it scans for the next `@` to start an entry, so an `@` anywhere in a
  comment gets parsed as a bogus entry and corrupts every entry after it in
  that file, with no error until BibTeX also fails to find the *citations*
  that vanished. Never put a literal `@` character in a `.bib` comment, even
  to name the problem.
- **`Warning--I didn't find a database entry for "<key>"`** — a real missing
  reference, not a build bug: the citation key is used in the `.qmd` but not
  defined in either `references.bib` or `survey.bib`. Add the entry or fix the
  key; do not fabricate one.

## Files
- `manuscript_marine.qmd` — the draft (edit this). Prose is Markdown with
  `[@key]` citations; tables/figures/equations are raw LaTeX passed through to
  PDF.
- `_preamble.tex` — extra LaTeX loaded into the rendered document.
- `build.py` — the one-command build.
- `build_survey.py` — generates `survey.bib` + `appendix_table.tex` from
  `../literature/dvv_processing_parameters.csv` and the Crossref cache. Every one
  of the 103 surveyed studies is cited in the appendix `longtable`
  (Table~\ref{tab:survey}).
- `references.bib` — hand-curated narrative bibliography (foundational + stats
  refs). `survey.bib` is auto-generated and reuses these keys where a surveyed
  study is already cited here, so each paper is listed once.

## Figures
Every figure is one of the demo figures in
[`../literature/figs/`](../literature/figs) — regenerate them with
`pixi run python literature/synthetic_dvv_demo.py` (or `build.py --figures`).

## To submit to GJI
The rendered `manuscript_marine.tex` builds with `pdflatex`/`lualatex` +
`bibtex`. To adopt the official class, set `documentclass: gji` in the
`manuscript_marine.qmd` front matter (and move the abstract into the GJI
`\begin{summary}` environment in a post-process, since Quarto emits
`\begin{abstract}`).

## Status / TODO
- The manuscript source was renamed `manuscript.qmd` → `manuscript_marine.qmd`.
  The old `manuscript.qmd`/`manuscript.tex` are stale and should be removed
  from the repo (`git rm paper/manuscript.qmd paper/manuscript.tex`) once this
  name is confirmed final — see *Committing* in the top-level repo docs.
- **Authorship** is a placeholder (`M. A. Denolle` + co-authors TBD).
- Title, abstract and section text are a first complete draft, not final.
- Sections `\ref{sec:multiverse}` (multiverse) and `\ref{sec:bayes}` (Bayesian
  measurement model) are wired to the `codameter.deviations` and
  `codameter.uq_bayes` experiments.
