# Short paper draft (GJI)

Draft manuscript: **"Processing choices, not physics: the reproducibility cost of
ad-hoc decisions in ambient-noise seismic velocity-change monitoring."**

A short *Geophysical Journal International* paper built on the
[`literature/`](../literature) survey and the executable
[`codameter.synthetic_demo`](../src/codameter/synthetic_demo.py) framework. Every
figure is one of the demo figures in [`../literature/figs/`](../literature/figs)
— regenerate them with `pixi run python literature/synthetic_dvv_demo.py`.

## Files
- `manuscript.tex` — the draft (standard `article` class so it builds anywhere).
- `references.bib` — bibliography.

## Build
```
cd paper
pdflatex manuscript && bibtex manuscript && pdflatex manuscript && pdflatex manuscript
```
(`\graphicspath` points at `../literature/figs/`, so build figures first.)

## To submit to GJI
Swap the class for the official one and move the abstract into the GJI summary
environment:
```latex
\documentclass{gji}      % from https://academic.oup.com/gji (LaTeX template)
...
\begin{summary} ... \end{summary}   % instead of \begin{abstract}
```

## Status / TODO
- **Authorship** is a placeholder (`M. A. Denolle` + co-authors TBD).
- Title, abstract and section text are a first complete draft, not final.
- Consider adding: a short methods appendix with the estimator equations; a
  reporting-checklist table; and a real-data companion example.
