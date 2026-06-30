# dv/v passive-monitoring literature survey

A shareable, literature-derived database of the **processing parameters and
best-practice value ranges** used for ambient-noise / coda **seismic
velocity-change (dv/v) monitoring**, organized by science application
(volcanoes, earthquakes/faults, landslides, groundwater/hydrology, cryosphere,
geothermal/reservoir) plus a methodology group of the papers that define how
parameters *should* be chosen.

Built to support the `codameter` measurement-design work (see
[../src/codameter/uq_measurement.py](../src/codameter/uq_measurement.py)): the
columns mirror the knobs scored there — frequency band, lapse-time (coda)
window, stacking, dv/v method, station geometry, and depth sensitivity.

## Files

| File | What it is |
| --- | --- |
| [dvv_processing_parameters.csv](dvv_processing_parameters.csv) | **Master table** (103 unique studies), machine-readable, all columns. Open in Excel / Sheets / pandas. |
| [dvv_processing_parameters.md](dvv_processing_parameters.md) | Rendered table grouped by application, with clickable DOI links. |
| [best_practices.md](best_practices.md) | Consolidated best-practice rules and recommended parameter ranges per application. |
| `raw/*.json` | Per-application scan output (provenance), before deduplication. |
| `build_table.py` | Regenerates the CSV + Markdown from `raw/`. Run `python literature/build_table.py`. |
| `build_quarto_refs.py` | Enriches DOIs via Crossref (cached) and writes the Quarto references page `../quarto/survey-references.qmd`. |

The survey is also published on the Quarto site as three pages:
[`quarto/survey-best-practices.qmd`](../quarto/survey-best-practices.qmd) (the
synthesis), [`quarto/survey-references.qmd`](../quarto/survey-references.qmd)
(full Crossref-enriched citations with DOI links), and
[`quarto/survey-synthetic-demo.qmd`](../quarto/survey-synthetic-demo.qmd) (the
synthetic demonstration below).

## Synthetic demonstration — how processing choices move dv/v

`synthetic_dvv_demo.py` builds noisy synthetic CCFs that repeat over time with a
**known** ground-truth dv/v(t) per application, then recovers dv/v under
different processing choices — so every gap between the recovered curve and the
truth is an artefact of a *choice*, not of nature. The core (CCF synthesis,
stretching & MWCS estimators, truth generators, figure builders) lives in the
package at
[`codameter.synthetic_demo`](../src/codameter/synthetic_demo.py) and is unit-
tested in [`tests/test_synthetic_demo.py`](../tests/test_synthetic_demo.py).

Run `pixi run python literature/synthetic_dvv_demo.py` → writes nine figures to
`literature/figs/`. **All seven** NoisePy `monitoring_methods` estimators are
reproduced live — TS, WCC, DTW, MWCS, and the wavelet-domain WCS (with 2-D phase
unwrapping, Mao 2020), WTS, WTDTW (Morlet CWT, no external dependency) — and
benchmarked as in Yuan et al. (2021). The focus is **deviations from best
practice** and the **undocumented choices** that break intercomparability:

| Figure | Theme | Deviation / consequence |
| --- | --- | --- |
| `demo_1_methods.png` | Estimator choice (7 NoisePy methods, Yuan 2021) | MWCS cycle-skips; 2-D-unwrapped WCS recovers; warps (DTW, WTDTW) under-shoot |
| `demo_2_aggregation.png` | Cross-component aggregation | avg-dv/v vs avg-CC-images, weighted vs not → different value & uncertainty |
| `demo_3_uncertainty.png` | Station-pair aggregation & σ | Same mean, reported 1σ differs ~√N (SE vs SD, weighted vs not) |
| `demo_4_frequency_depth.png` | Frequency band → depth | Band selects depth → a different signal |
| `demo_5_window_band.png` | Coda window vs band | A fixed late window is pure noise at high frequency |
| `demo_6_stacking.png` | Stacking length | Long stack smears/delays the coseismic step |
| `demo_7_reference.png` | Reference strategy | Moving ref erases trend; Brenguier 2014 inversion is robust |
| `demo_8_artifacts.png` | Clock error + late-coda noise | Spurious dv/v (branch-antisymmetric clock; spurious seasonal) |
| `demo_9_multiverse.png` | 27 pipelines | Spread across choices ≈ size of the signal |
| `demo_10_deviations.png` | One-at-a-time best-vs-deviation | Each deviation ranked by RMS bias + drop distortion (`codameter.deviations`) |
| `demo_11_multiverse.png` | Full factorial (108 pipelines) | Spread + first-order variance attribution: which choice controls dv/v |
| `demo_12_bayes.png` | Bayesian processing-ensemble inversion | Posterior dv/v + time-dependent data covariance C_d (`codameter.uq_bayes`) |

Figures `demo_1`–`demo_9` come from `synthetic_dvv_demo.py`; `demo_10`–`demo_11`
from `python -m codameter.deviations` (the deviation ranking + ultimate
multiverse); `demo_12` from `python -m codameter.uq_bayes` (the Bayesian
measurement model — the *new* best practice that marginalises the processing
choice into a single time-dependent covariance for downstream inversion).

## How to extend it

1. Add rows to the relevant `raw/<application>.json` file (same keys as existing rows).
2. Re-run `python literature/build_table.py`.

To fill in `n/r` cells, the per-study DOI links are in the table — open the paper
and read the processing/methods section.

## Column definitions

| Column | Meaning |
| --- | --- |
| `application` | Primary science purpose: Volcano, Earthquake/Fault, Landslide, Groundwater/Hydrology, Cryosphere, Geothermal/Reservoir, Methodology. |
| `also_applications` | Other groups the same paper appeared in (foundational papers span several). |
| `authors_year` | Citation. |
| `year` | Publication year. |
| `target_process` | Physical change being inferred (magma pressurization, coseismic damage, pore pressure, freeze-thaw, …). |
| `region_site` | Study area / volcano / fault / aquifer / test dataset. |
| `signal_source` | Ambient noise, Earthquake coda, or Both. |
| `components` | Correlation components (ZZ, RR, TT, single-station cross-component, autocorrelation, …). |
| `freq_band_hz` | Frequency band(s) in Hz. |
| `coda_window_s` | Lapse-time / coda window in seconds. |
| `dvv_method` | Stretching, MWCS, Wavelet, DTW, or Other. |
| `stack_scheme` | Reference-stack choice + substack length. |
| `station_config` | Single-station autocorr, Single-station cross-comp, Station pairs, or Array. |
| `depth_sensitivity` | Inferred sensing depth / depth range. |
| `dvv_amplitude` | Typical observed dv/v magnitude. |
| `uncertainty_treatment` | How errors / uncertainty were handled. |
| `best_practice_note` | One-line takeaway on the parameter choice or the rule the paper establishes. |
| `doi_url` | Clickable DOI / publisher link. |
| `open_access_format` | HTML, PDF, paywall, or preprint. |

`n/r` = **not reported** in the source as scanned; it was deliberately not
guessed. Paywalled papers carry more `n/r` cells because internal parameters
could not be verified from the abstract alone — these are the highest-value
cells to fill by hand.

## How it was built

Six parallel literature scans (one per application group) ran live web searches
across the published journal literature, extracted parameters from abstracts /
open-access full text, and recorded a verified DOI per paper. Results were then
deduplicated by DOI (117 raw rows → 104 unique studies). Papers that could not
be verified were dropped rather than invented.

### Caveats and items to spot-check

- **DOIs corrected via Crossref** (the original scan had wrong DOIs that resolved
  to unrelated papers): Bièvre 2018 → `10.1016/j.enggeo.2018.08.013`; Voisin 2016 →
  `10.1190/int-2016-0010.1` (*Interpretation*, not Eng. Geol.); Fan 2023 →
  `10.1016/j.enggeo.2022.106922`; Mikesell 2015 → `10.1093/gji/ggv138`. The
  "Morimachi 2024" entry was **removed** — it could not be verified (placeholder
  author name; no matching paper in Crossref). Kristjánsdóttir 2019 is an **EGU
  conference abstract** (ADS link, not a journal DOI); Pacheco & Snieder 2005
  (JASA) is a valid DOI absent from Crossref. These three lack enriched metadata
  and show the short citation on the references page.
- All DOIs were cross-checked by comparing the Crossref title against each row's
  topic (`build_quarto_refs.py` + an automated title/author audit).
- **Corrected attributions:** Obermann et al. 2013 is in *GJI* (not JGR);
  Rubinstein & Beroza 2005 concerns the **2004 Parkfield** event; "Clements &
  Denolle 2023 Geophysics" does not exist — the real paper is *JGR: Solid Earth*
  (e2022JB025553); DOI `10.1186/s40623-020-01311-1` is **Andajani et al. 2020**
  (a duplicate "Nimiya 2020" was removed).
- **Coverage is a first broad pass, not exhaustive.** It skews toward the
  best-studied targets (Piton de la Fournaise, Kīlauea, Japanese Hi-net,
  California, Alpine landslides). Sparse-literature targets (e.g. Nevado del Ruiz,
  Mayotte) are under-represented.
- Scope is **dv/v passive monitoring only** (per project decision). Fluvial
  seismology (river discharge / sediment transport from seismic power) and
  landslide *detection* are intentionally excluded; they use power-spectral, not
  dv/v, methods.
