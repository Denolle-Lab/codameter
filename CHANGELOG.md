# Changelog

All notable changes to `codameter` will be documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- **`run_pipeline(..., return_cc=True)`** — optionally return the per-epoch
  stretching correlation coefficient alongside `(dvv, valid)`, for
  coherence-based error models (`uq_measurement.weaver_stretching_error`).
  Works for fixed and moving references with the stretching estimator; NaN
  otherwise. The default two-tuple return and all gating behavior are
  unchanged (CC-gating remains fixed-reference-only).
- **`run_pipeline(..., prefiltered=True)`** — accept CCFs already band-passed
  at `cfg["band"]` and skip the estimators' internal band-pass, so callers
  evaluating several stack/reference variants at the same band filter the raw
  matrix once. Exact to float rounding because the band-pass is linear and
  commutes with linear stacking; only valid at an identical band and only for
  the estimators whose band usage is that one linear filter (stretching, WCC,
  DTW, MWCS — the wavelet estimators raise).
- **`measure_stretching_trailing`** — vectorized stretching against a trailing
  (moving) reference. The stretched sample positions `t/(1+eps)` are
  data-independent, so the interpolation gather indices/weights are computed
  once per epsilon and applied to all days at once; trailing references come
  from a cumulative sum and the band-pass runs once over the whole matrix.
  `deviations._moving_reference` dispatches to it for the stretching
  estimator (~3x on the 3-year volcano synthetic, observed 3-4.5x across
  repeated runs), keeping the generic per-day loop for the other estimators.

### Changed

- **`_trailing_stack`** is now a difference of float64 cumulative sums —
  O(ndays x nlag) independent of the stack length instead of
  O(ndays x k x nlag) (~2x at k=45). All three fast paths reproduce the
  replaced per-day loops to ~1e-15 in dv/v, enforced by regression tests at
  atol=1e-12; combined, a 5-member same-band ensemble drops ~3x in runtime.
  (Speedups are wall-clock, measured on one machine and noisy run to run —
  re-benchmark before citing a more precise figure than "roughly Nx".)

## 0.3.0 — 2026-07-27

### Added

- **Hideable golden set** — a truth-free agent view of the golden benchmark
  (secret truth parameters withheld, a public sample exposed), with a
  pip-installable generator and a `--exclude-public` toggle for scoring runs
  that must not leak ground truth.
- **`codameter-bench`** — a shardable config-sweep CLI for running the
  benchmark on Fargate/Batch, with a bench plan sized to the loaded corpus.
- **2D radiative-transfer coda envelope** (`rt_envelope_2d`,
  `make_freqdep_coda`) — replaces the ad hoc exponential coda envelope with
  the exact single-scattering solution for isotropic scattering (Sato 1993;
  Paasschens 1997), including frequency-dependent absorption so high-frequency
  coda decays faster than low-frequency coda, as in real data.
- **Causal/acausal branch-asymmetry tools** (`impose_dvv_branch`,
  `branch_daily_ccfs`, `branch_combines`, `fig_branch_asymmetry`) — test
  whether taking the branch with the larger measured change is defensible
  given measurement-error asymmetry between the two branches.
- **`coda_window_from_envelope`** — picks a coda window automatically by
  tracking a reference stack's envelope and stopping where it flattens onto
  the noise floor, instead of a hand-tuned window per frequency band.
- **`paper/manuscript_marine.qmd`** — the GJI draft now builds natively under
  the real `gji.cls`, with a GitHub Action syncing the built manuscript and
  figures to a paper-only repo that Overleaf's GitHub Sync reads from.

### Changed

- **Breaking:** the FrugalMind suite `dataset_id` is renamed from
  `dvv_processing` to `codameter` (`src/codameter/frugalmind.py`), changing
  the suite/CLI name and the exported JSONL path
  (`datasets/codameter/v0.1/*.jsonl`). Harnesses pinned to a version before
  this change must update their suite name when they upgrade past it.

## 0.2.1 — 2026-07-12

### Fixed

- Validate the golden manifest version and self-heal a corrupt or stale
  per-user cache (re-derive from the authoritative manifest) instead of
  raising on an out-of-date cache.
- Fix the golden data directory resolution when installed via pip.

### Added

- Workflow chart on the narrative site (navbar "Workflow").

## 0.2.0 — 2026-07-11

### Added

- **Graded golden benchmark** — 30 cases (easy/medium/hard, multi-channel
  hard), with the hard grade depth- and frequency-dependent, and FrugalMind-suite
  compatible (`golden.recover`, depth-aware grid).
- **`codameter.deviations`** — best-practice baseline plus a documented
  deviation menu (estimator, band, coda window, stack, reference, gating). One
  function ranks each deviation by the bias and drop-distortion it injects on a
  truth-known synthetic (`oat_effects`); another runs the **full factorial
  multiverse** of all choice combinations and attributes the outcome variance to
  each axis with a first-order (Sobol/ANOVA) sensitivity index (`multiverse`).
  Figures `demo_10_deviations.png`, `demo_11_multiverse.png`.
- **`codameter.uq_bayes`** — a Bayesian hierarchical measurement model that
  treats the processing choice as a nuisance parameter, runs an ensemble of
  defensible pipelines, and marginalises the choice out with a conjugate Gibbs
  sampler. Returns the posterior `δv/v(t)` and the **time-dependent data
  covariance `C_d`** (within ⊕ methodological, temporal correlation, common-mode)
  for downstream inversion. Figure `demo_12_bayes.png`; new Quarto page
  `theory-bayesian-measurement.qmd`.
- **`paper/manuscript.qmd`** — the GJI draft is now authored in Quarto Markdown;
  `python paper/build.py` renders it to `manuscript.tex` + `manuscript.pdf` and
  regenerates the 103-study appendix survey table (`build_survey.py`,
  `appendix_table.tex`, `survey.bib`) so every surveyed study is cited.
- The 103-study processing-parameter survey now also renders as a scrollable
  table on the measurement-UQ Quarto page.

## 0.1.0 — 2026-04-29

Initial release. Implements the v0.1 scope of the build plan.

### Added

- **Phase 0 — data ingestion.** Generic `load_dvv()`, `load_csv_timeseries()`,
  and `load_earthquake_catalog()` loaders for CSV / parquet / feather, with
  automatic time-column detection and `pyarrow`-backed feather support.
  QC summary (gap detection, outlier flagging) via `data/qc.py`. Forcing
  alignment via `data/covariates.py`.
- **Phase 1 — site characterisation.** `VelocityProfile` dataclass,
  `make_fine_model()` for disba-ready discretisation, depth-frequency
  table via either the `Vs/(3f)` rule of thumb or a `disba` Rayleigh-wave
  kernel (optional dependency).
- **Phase 2 — Tier 1 coupling diagnostics.** `drainage_peclet()`,
  frequency-dependent `frequency_dependent_beta_eff()` (Eq. 15 of Denolle,
  in prep), `tidal_beta_estimate()`, and a two-tier escalation decision
  tree (`escalation_decision`).
- **Phase 3 — design matrix.** `build_predictor_matrix()` constructs the
  linear-superposition design (Eq. 6) for any combination of hydrological,
  thermoelastic, and damage forcings.
- **Phase 4 — linear inversion.** `linear_fit()` performs weighted
  least-squares with closed-form Gaussian posterior and reduced-χ² output.
  Intercept handling, missing-data masking, and parameter-name traceability.
- **Phase 5 — anomaly detection.** Ljung–Box whiteness test, rolling
  z-score transient detection, and a structured `AnomalyReport`.
- **Phase 6 — interpretation.** β-bridge relation
  ($\beta = -\mu' \kappa / 2\mu$), pressure-sensitivity propagation,
  and constraint of $\mu'$ from the fitted hydrological coefficient.
- **Forward physics.**
  - `forward/thermoelastic.py` — Berger (1975) skin-depth diffusion,
    Fourier-harmonic decomposition (Ermert et al. 2023), phase-shift mode.
  - `forward/poroelastic.py` — Roeloffs (1988), Talwani et al. (2007)
    precipitation series, Okubo et al. (2024) GWL proxy.
  - `forward/damage.py` — Snieder et al. (2017) closed-form healing kernel.
  - `forward/loading.py` — Tsai (2011) surface-load forward model.
  - `forward/capillary.py` — Tier 4 stub for v0.4.
- **Public API.** `run_workflow()` high-level entry point + `Site`
  dataclass + the six `PhaseN` classes for low-level control.
- **CLI.** `codameter run --config X`, `codameter validate --config X`
  (pre-flight configuration check), and `codameter cd2023
  --data-dir Y --station Z`. The `cd2023` subcommand wires directly
  to the Clements & Denolle (2023) Zenodo archive.
- **Examples.**
  - `examples/01_parkfield_synthetic.py` — synthetic Parkfield
    end-to-end demo, recovering truth amplitudes within 4σ.
  - `examples/02_clements_denolle_2023.py` — synthetic-or-real C&D 2023
    test harness, recovering truth amplitudes within 4σ in synthetic mode.
  - `examples/configs/{parkfield,cascadia,kilauea,clements_denolle_2023_LJR}.yaml`.
- **Tests.** 100+ unit and integration tests covering forward models,
    coupling diagnostics, kernels, linear inversion, data loaders, the
    forcing-model registry, and the full six-phase pipeline. Core modules
    at 80–90+% coverage. Run `pytest` to see the current count; one test
    is skipped unless the optional `disba` extra is installed.
- **CI.** GitHub Actions workflows for lint + pytest (Linux & macOS,
  Py 3.10–3.12), docs build, and PyPI/Zenodo release on tag.
- **Docs scaffold** — mkdocs + mkdocstrings (`docs/*`).

### Known issues

See [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md). Headline items:

- Sign convention in `snieder_healing` does not match its docstring; the
  inversion handles this internally so recovery is unaffected.
- Phase 4 coupled inversion (MCMC) is deferred to v0.2.
- Tiers 2, 3, 4 coupling diagnostics deferred to v0.3 / v0.4.
- Water-table inversion deferred to v0.2.
