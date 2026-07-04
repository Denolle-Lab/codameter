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

For production/acceptance, the emitted **`manuscript.tex`** can be dropped into
the official **`gji.cls`** template (from the GJI author resources) and the
reference style switched to `gji.bst`; the content is already structured for it.
Co-authors, author contributions, and a competing-interests statement remain to
be filled before submission.

## Edit in Markdown, get TeX + PDF

The **single editable source is [`manuscript.qmd`](manuscript.qmd)** (Quarto
Markdown). You never edit LaTeX by hand. One command renders it:

```
python paper/build.py
```

This:
1. regenerates [`survey.bib`](survey.bib) + [`appendix_table.tex`](appendix_table.tex)
   from the literature CSV (`build_survey.py`), and
2. runs `quarto render manuscript.qmd --to pdf`, which (with `keep-tex: true`)
   emits both **`manuscript.tex`** (submission-ready LaTeX) and **`manuscript.pdf`**.

So: **`manuscript.qmd` → `manuscript.tex` → `manuscript.pdf`.** `manuscript.tex`
is a *generated* artifact — do not edit it.

Options:
```
python paper/build.py --figures     # also regenerate the demo figures first
python paper/build.py --no-survey   # skip regenerating the survey table/bib
```

## Files
- `manuscript.qmd` — the draft (edit this). Prose is Markdown with `[@key]`
  citations; tables/figures/equations are raw LaTeX passed through to PDF.
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
The rendered `manuscript.tex` builds with `pdflatex`/`lualatex` + `bibtex`. To
adopt the official class, set `documentclass: gji` in the `manuscript.qmd` front
matter (and move the abstract into the GJI `\begin{summary}` environment in a
post-process, since Quarto emits `\begin{abstract}`).

## Status / TODO
- **Authorship** is a placeholder (`M. A. Denolle` + co-authors TBD).
- Title, abstract and section text are a first complete draft, not final.
- Sections `\ref{sec:multiverse}` (multiverse) and `\ref{sec:bayes}` (Bayesian
  measurement model) are wired to the `codameter.deviations` and
  `codameter.uq_bayes` experiments.
