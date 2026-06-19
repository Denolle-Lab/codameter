# Changelog

All notable changes to `codameter` will be documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

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
