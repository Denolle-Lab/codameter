# Changelog

All notable changes to `codameter` will be documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- `golden.advisory_case`: public seasonal development examples for all six
  applications, independent of private evaluation records. Advisor snippets
  use per-channel recovery, fixed scoring support, and report availability.
  Conditional synthetic checks no longer claim proof of field performance
  or statistical equivalence from one seeded RMS comparison. (AG-01/02/03)

### Fixed

- Enlarge the calibration table, preserve nonzero Monte Carlo standard errors,
  correct abstract percent formatting, and keep the running title within the
  page margin. (FIG-03, FMT-01)

- Reject non-daily CCF input in the processing ensemble. Already measured
  irregular series remain supported by `gibbs_dvv`. Moving-reference and
  non-stretching ensemble members now honor the coherence gate. (UQ-05)
- Calibration excludes unavailable member epochs, including invalid floors,
  from conditional coverage and reports their availability separately.
  The archived 600 locked runs have zero missing fraction; their reported
  results are unchanged by this correction. (SCI-05)
- Include use-case synthesis geometry source in golden cache identity. (DET-02)
- Distinguish joint hierarchical fitting from pipeline mixture marginalization
  in the manuscript and API. Near-nominal 95% pointwise member coverage does
  not establish covariance calibration: 68% intervals overcover, and the
  combined estimate's credible band undercovers. Downstream covariance and
  shared errors remain unvalidated. (UQ-03/04, INV-01)
- Correct field-data availability and review-adjudication statements to
  reflect the missing run provenance and pending author inputs. (REP-02, COMP-01)

### Added

- `codameter.calibration`: repeated-realisation coverage calibration of the
  Bayesian measurement covariance (`python -m codameter.calibration --n 200
  --scenario clean|shared_source|clock_drift --out ...`): pointwise 68/95 percent coverage
  of member errors, credible-band coverage of the combined estimate, width,
  bias, RMSE and failures per realisation, with standard errors across
  realisations and a predefined acceptance margin. (SCI-05)

- `codameter.figures`: one driver for every generated paper figure
  (`python -m codameter.figures --out literature/figs`). Each figure is
  written with a `.npz` sidecar holding every plotted array (and the
  generator's result arrays under `data/`) and a `.json` sidecar with the
  generator, codameter version, git commit, timestamp, library versions and
  an inventory. `paper/build.py --figures` uses it; previously the build ran
  only the `synthetic_demo` subset and six of the manuscript's figures had
  no generator in the build (2026-09-10 audit, REP-01). The three real-data
  figures are documented as external in `literature/figs/SOURCES.md`.

### Changed (BREAKING)

- **The Bayesian ensemble runs every configuration through the canonical
  pipeline** (`deviations.run_pipeline`): `reference` (`fixed`/`moving`) and
  `gate` now take effect (they were ignored), stacking happens on the daily
  grid and only the output is decimated by `cadence` (a 10-day stack used to
  span 27 days at cadence 3), epochs a configuration cannot produce are NaN
  and treated as missing, and coherence below `MIN_COHERENCE` gives a
  missing floor instead of being clipped to 0.5. `reference="inversion"` is
  rejected. Member labels now include stack, reference and gate. (UQ-05)

- **`gibbs_dvv` builds its smoothness prior on the physical time grid**
  (`second_difference_operator`: exactly `[1, -2, 1]` on a regular grid, and
  a curvature penalty that scales with the interval across gaps), accepts
  missing members (zero precision), and reports `beta_mean` and `n_obs`.
  The per-epoch decomposition no longer counts the within-method floor
  twice: `method_std**2` is the between-configuration variance of the
  offset-corrected members minus the calibrated floor, floored at zero, and
  `total_std**2` is their sum. `Cd` is documented as a constructed
  measurement covariance that cannot represent an error shared by every
  configuration (tested as a documented limitation). (UQ-03, UQ-04, UQ-05)

- **`weaver_stretching_error` now requires the band width** (`bandwidth_hz`;
  or call `weaver_stretching_error_band(cc, (f1, f2), t1, t2)`). It implements
  Weaver et al. (2011) eq. 20 with the `sqrt(1-X^2)/(2X)` prefactor and the
  spectral timescale `T = sqrt(ln 10) / (pi B)` (band edges at the -10 dB
  points of Weaver's Gaussian spectrum; `bandwidth_timescale`). The native
  form is exposed as `weaver_rms_dilation(cc, omega_c, t1, t2, T)` and is
  tested against Weaver's own numerical example (their eq. 21). The previous
  implementation omitted `T`, so its result was not dimensionless and did not
  depend on band width, and used `(1-CC^2)/(2CC^2)` for the variance, twice
  Weaver's. Found by the 2026-09-10 pre-submission audit (UQ-01).
  `ProcessingChoice` gains a `bandwidth_hz` field and `ProcessingPrior` a
  `relative_bandwidth` (default 2/3, a one-octave band). In the Bayesian
  ensemble the fitted rescale `s` absorbs the constant; only the relative
  weights of members in different bands change.

- **`per_band_marginal_error` no longer adds the spread of the floors as a
  "processing-choice" variance.** That term has no probabilistic meaning: a
  mixture of zero-mean components with different precisions has marginal
  variance `E_c[sigma_c^2]` and no spread term. The processing-choice spread
  is now computed only from `conditional_means=` (the estimate each choice
  returns on the same data) and is zero otherwise. A `band_bias` is reported
  as `bias` and enters `rmse`, not the centred `sd` (`total` is kept as an
  alias of `sd`). Found by the 2026-09-10 pre-submission audit (UQ-02).

- **The golden scorers evaluate on a fixed support.** `frugalmind._gold` now
  records per case the epochs where the reference pipeline is valid
  (`support`) and the earliest 20% of them (`baseline`); both scorers call
  `golden.rms_on_support`, which demeans truth and prediction over that fixed
  datum and scores a missing (non-finite) prediction inside the support as
  the null prediction. Previously the support and the datum came from the
  submission's own finite values, so ten zeros followed by nulls scored 1.0
  on every public case. Export version is `v0.2`; `scorer_spec.config`
  carries the rule (`version: 2`). Expected metrics in the manifest are
  unchanged (the reference pipeline has no gaps on its own support). Found by
  the 2026-09-10 pre-submission audit (EV-01).

- **`linear_fit` no longer reports zero uncertainty for a parameter on an
  active bound.** The covariance keeps the unconstrained curvature and the
  new `LinearFitResult.at_bound` flags the parameter (also in `to_dict`).
  A one-sided interval needs a truncated-normal treatment. (INV-02)

- **`global_reference_inversion` checks the pair graph.** Each connected
  component gets its own sum-zero datum, a warning is issued when there is
  more than one, and an epoch with no pairs is returned as NaN in `dvv` and
  `sigma` instead of a spurious zero. `GlobalReferenceSolution` gains
  `component` and `n_components`. (INV-02)

- **The golden cache is exact and versioned.** `golden.generate` keys the
  cache on the recipe hash *and* a hash of the package version plus the
  synthesis source, stores float64 (the warm route used to return float32,
  differing from the cold route at the 1e-7 level), writes atomically,
  removes stale files for the case, and returns `recipe_hash` and
  `generator_hash` on every route. (DET-02)

- **`codameter-bench aggregate` refuses incomplete or duplicated input.**
  It requires every shard `k` of the declared `N`, each
  `(case_id, config_index)` cell exactly once, and one codameter version
  across rows (rows now carry `codameter_version`); `--allow-partial`
  accepts missing shards only. An `aggregate_manifest.json` records the
  inventory. `_read_jsonl_dir` now yields `(shard_name, row)`. (SCALE-02)

- **`gibbs_dvv` solves the smoothness-prior update in banded form** (the
  second-difference normal matrix is pentadiagonal), removing the dense
  `T x T` Cholesky per iteration; `solver="dense"` keeps the explicit path
  for equivalence tests. The module docstring no longer calls `Cd` the
  posterior covariance of `mu`. (SCALE-01, UQ-04 wording)

- **dv/v sign convention is now physical everywhere**: a velocity *increase*
  is positive; every estimator and `run_pipeline` return
  `dv/v = -eps / (1 + eps)` where `eps` is the stretch factor (exact at all
  orders — the first-order `-eps` differs by ~eps² which matters at
  landslide-scale changes). `impose_dvv`/`impose_dvv_branch` impose in the
  same physical convention. Previously the generator and all seven
  estimators consistently used the epsilon convention (positive = coda
  dilation = slowdown) — internally coherent, so synthetic recovery tests
  passed, but real-archive dv/v anticorrelated with the Clements-Denolle
  2022 product and with seasonal hydrology at three CI stations (found on
  the noisepy-dvv-cloud Gate 1 validation, 2026-08-08). Downstream code
  that negated codameter output to get physical dv/v must remove that
  negation.

- **The stretching-family trial-epsilon search now resamples `current`, not
  `reference`.** `stretching_cc`, `measure_stretching_trailing`, and
  `measure_wts` previously interpolated the *reference* waveform at trial
  positions `t/(1+eps)` and held `current` fixed; they now interpolate
  *current* at `(1+eps)*t` and hold `reference` fixed, matching the field's
  usual convention (the reference is the stable, often multi-day-averaged
  anchor; the current trace is the one being tested against it). **The exact
  conversion `dv/v = -eps/(1+eps)` is unchanged** — both conventions give
  the identical exact map (see the derivation in the PR), so this is not a
  second sign-convention flip; it is an internal numerics change with a
  small (single-digit-percent) shift in finite-sample results, since a
  different (per-day, typically noisier) trace is now the one being
  resampled. Added `synthetic_demo.dvv_to_epsilon` (the exact inverse of
  `eps_to_dvv`) and `synthetic_demo._stretch_window`, a common
  valid-support window shared across the whole epsilon grid so no trial
  epsilon is silently extrapolated and every candidate is scored on an
  identical sample count (warns and shrinks the window if the requested
  one would need extrapolation at the edges of `eps_max`; none of the
  packaged `use_cases.py` configs hit this).
  `tests/data/golden/manifest.json` regenerated against the new numerics
  (`golden.MANIFEST_VERSION` bumped 2 → 3 so stale per-user caches
  regenerate); a hidden/private golden corpus built with `private_golden.py`
  before this change should be regenerated too.

### Added

- `synthetic_demo.eps_to_dvv`: the exact stretch-to-velocity map.
- `tests/test_sign_convention.py`: every estimator is held to the physical
  convention, both signs, plus a `run_pipeline` end-to-end check — the
  permanent guard against convention drift.

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
  (moving) reference. The stretched sample positions `(1+eps)*t` are
  data-independent, so the interpolation gather indices/weights are computed
  once per epsilon and applied to all days at once; trailing references come
  from a cumulative sum and the band-pass runs once over the whole matrix.
  `deviations._moving_reference` dispatches to it for the stretching
  estimator (~3x on the 3-year volcano synthetic, observed 3-4.5x across
  repeated runs), keeping the generic per-day loop for the other estimators.
  (Updated below: the resampled trace is `current`, not `reference`.)

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
