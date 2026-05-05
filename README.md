# codameter

[![CI](https://github.com/Denolle-Lab/codameter/actions/workflows/ci.yml/badge.svg)](https://github.com/Denolle-Lab/codameter/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

**An operational six-phase workflow for interpreting relative seismic velocity
changes ($\delta v / v$) as stress and strain meters.**

`codameter` implements the workflow of Denolle (in prep, *JGR Solid Earth*)
as an executable Python pipeline. Given a $\delta v / v$ time series and the
relevant environmental forcings (temperature, precipitation, earthquake
catalog, etc.), the package extracts:

- depth-resolved stress estimates with propagated uncertainties,
- water-table-depth and saturation inversions (v0.2+),
- coupling-tier diagnostics that flag when linear superposition fails,
- anomaly classifications (tectonic, volcanic, hydrological, post-seismic,
  anthropogenic) for residual signal not explained by the physical model.

The repository is the operational counterpart to the manuscript-companion
[`dvv-coupled`](https://github.com/Denolle-Lab/dvv-coupled) repo (which
generates the JGR figures); `codameter` is the tool that any group can
apply to their own data.

> **Status — v0.1.** Phases 0, 1, 2 (Tier 1 only), 3 (linear), 5 (anomaly), and
> 6 (β-bridge stress at depth) are operational. Phase 4 coupled MCMC and Tiers
> 2–4 are scheduled for v0.2 / v0.3.

---

## Installation

```bash
# core install (numpy / scipy / pandas / matplotlib only)
pip install codameter

# with disba sensitivity kernels (Phase 1)
pip install "codameter[kernels]"

# everything — kernels, MCMC backend, dev tools
pip install "codameter[all]"
```

From source:

```bash
git clone https://github.com/Denolle-Lab/codameter.git
cd codameter
pip install -e ".[dev]"
pre-commit install
pytest
```

---

## 60-second quickstart

```python
from codameter import run_workflow

result = run_workflow(
    dvv_data="parkfield.parquet",
    forcings={
        "temperature":   "T.csv",
        "precipitation": "P.csv",
        "earthquakes":   "eq.csv",
    },
    site_config="examples/configs/parkfield.yaml",
)

result.summary()                   # text summary of all six phases
fig = result.plot_phases()         # six-panel diagnostic figure
result.export("runs/parkfield/")   # all artifacts to disk
```

The same task from the command line:

```bash
codameter run --config examples/configs/parkfield.yaml \
                 --output runs/parkfield/
```

For the phase-by-phase API and the low-level physics modules, see
[`docs/quickstart.md`](docs/quickstart.md) and
[`docs/workflow.md`](docs/workflow.md).

---

## Apply to the Clements & Denolle (2023) California dataset

The repository ships with a config and an example notebook that run the
workflow end-to-end on a station from the Clements & Denolle (2023) JGR
dataset, available from [Zenodo (DOI 10.5281/zenodo.6413275)](https://doi.org/10.5281/zenodo.6413275).

```bash
# 1. Download the C&D 2023 archive (4.4 GB) and unpack
mkdir -p data/clements_denolle_2023
cd data/clements_denolle_2023
curl -L -O https://zenodo.org/records/6413275/files/data-0.2.0.zip
unzip data-0.2.0.zip
cd ../..

# 2. Run the example
python examples/05_clements_denolle_demo.py \
    --station CI.LJR \
    --data-dir data/clements_denolle_2023 \
    --output runs/CI.LJR/
```

The loader in `codameter.data.loaders.load_clements_denolle_2023()` reads
the Arrow / Feather output of the upstream Julia pipeline (`03-dvv-comp.jl`)
and converts it to the standard `codameter` format.

---

## The six phases

| Phase | What it does | v0.1 status |
|---|---|---|
| **0** Data ingestion | QC, gap detection, time alignment | ✅ |
| **1** Site characterization | $V_S(z), \mu(z), \beta(z)$; sensitivity kernels via `disba` | ✅ |
| **2** Coupling diagnostics | Tier 1 (poroelastic) tidal-$\beta$, drainage Péclet | ✅ Tier 1; ⏳ Tiers 2–4 |
| **3** Linear regression | Eq. 6 weighted least squares, residual whiteness tests | ✅ |
| **4** Coupled inversion | Eq. 21 state-dependent (MAP + MCMC) | ⏳ v0.2 |
| **5** Anomaly detection | Whiteness, transient detection, attribution | ✅ basic |
| **6** Interpretation | $\beta$-bridge → stress at depth | ✅ trend only; ⏳ water-table v0.2 |

---

## Models, hyperparameters, and physical bounds

### Where to find them in the code

| What | File | Object / constant |
|---|---|---|
| Material-property priors | `src/codameter/config.py` | `MaterialProperties`, `Prior` |
| Physical validity checks on priors | `src/codameter/inverse/priors.py` | `validate_priors` |
| Thermal time-shift search grid | `src/codameter/inverse/linear_fit.py` | `DEFAULT_TIME_SHIFT_GRID_DAYS` |
| Forward-model defaults | `src/codameter/inverse/linear_fit.py` | `build_predictor_matrix` kwargs |
| Hard sign-constraint on regression coefficients | `src/codameter/workflow.py` | `_PHYSICAL_PARAM_BOUNDS` |

---

### Hydrological forward models

| Model key | Physics | Key hyperparameters | Physical bounds |
|---|---|---|---|
| `"baseflow"` (aliases: `"okubo_gwl"`, `"okubo2024"`) | Exponential-decay recharge/baseflow (linear reservoir; Sens-Schoenfelder & Wegler 2006; Okubo et al. 2024 Eq. 4) | `porosity` (default 0.05), `decay_rate_per_s` (default 1 / 180 d) | porosity ∈ (0, 0.6] |
| `"talwani"` | Full Biot convolution — undrained erf + drained erfc (Talwani et al. 2007; Clements & Denolle 2023 Eq. 9) | `depth_m` (default 100 m; C&D 2023: 500 m), `diffusivity_m2_s` (default 0.01; C&D range: 5×10⁻⁵–∞), `skempton_B` (default 0.6), `poisson_undrained` (default 0.3) | skempton_B ∈ [0, 1]; depth_m > 0 |
| `"drained"` | Drained-only erfc term — limiting case of Talwani when Skempton's B → 0 | `depth_m`, `diffusivity_m2_s` (same defaults as talwani) | depth_m > 0 |
| `"cdm"` | Cumulative Departure from k-day rolling Mean (Clements & Denolle 2023, CDMk) | `window_days` (default 365×8 = 2920 d; C&D 2023 optimise k ∈ [365, 365×14] d). Pass `precipitation_warmup_m` to pre-initialize the rolling mean | window_days ≥ 1 |
| `"precomputed"` | External GWL proxy passed directly (e.g. GRACE, well level). No forward model applied; column is only centred. | — | — |

### Thermoelastic forward model

| Model key | Physics | Key hyperparameters | Physical bounds |
|---|---|---|---|
| `"phase_shift"` | Annual surface-temperature cycle with a fixed phase lag τ_T (Berger 1975; Richter et al. 2014; Okubo et al. 2024) | `time_shift_days` (default 50 d at Parkfield; Clements & Denolle 2023 optimise τ_T ∈ [0, 200] d; LJR optimum ≈ 100 d). Fitted by chi-square profiling on `DEFAULT_TIME_SHIFT_GRID_DAYS = np.arange(0, 201, 1)` days. | τ_T ≥ 0 |

### Surface-loading forward models

| Model key | Physics | Key hyperparameters | Physical bounds |
|---|---|---|---|
| `"instantaneous"` | Static elastic compression by the instantaneous rain water column (Tsai 2011; Fokker et al. 2021) | `loading_bulk_modulus_GPa` (default 1.0 GPa) | — |
| `"snowpack"` | Accumulating SWE load with exponential melt | `snowpack_decay_rate_per_s` (default 1 / 30 d) | — |

---

### Material-property priors (`MaterialProperties`)

All priors are **Gaussian N(mean, std)** and are defined in `src/codameter/config.py`.
In v0.1 (WLS) they are not used in the inversion — they feed the Phase 6 uncertainty-propagation step.
In v0.2+ (MCMC) they act as proper prior distributions.

| Parameter | Default N(mean, std) | Physical bounds enforced | Where used |
|---|---|---|---|
| `beta_prior` | N(240, 80) dimensionless | — | Phase 6 β-bridge → stress at depth |
| `mu_prime_prior` | N(250, 90) dimensionless | — | Phase 6 μ' constraint |
| `porosity_prior` | N(0.05, 0.02) | (0, 0.6] — `validate_priors` raises if 3σ exceedance | `baseflow` forward model; Phase 6 |
| `skempton_B_prior` | N(0.6, 0.15) | [0, 1] — `validate_priors` raises if 3σ exceedance | `talwani` forward model; Phase 6 |
| `biot_alpha_prior` | N(0.8, 0.1) | [0, 1] — `validate_priors` raises if 3σ exceedance | Phase 6 |
| `hydraulic_diffusivity_prior_log10` | N(0.0, 1.0) log₁₀(m²/s) | — | Phase 6 |

Physical bound validation is implemented in `src/codameter/inverse/priors.py::validate_priors`.

---

### Hard physical sign-constraints on regression coefficients

Defined as `_PHYSICAL_PARAM_BOUNDS` in `src/codameter/workflow.py` and enforced
via bounded-variable least squares (`scipy.optimize.lsq_linear`, method `"bvls"`)
in Phase 4.

| Parameter | Bound | Physical reason |
|---|---|---|
| `p1_dGWL` | ≤ 0 | Rising water table (dGWL > 0) compresses and slows seismic velocity, so dv/v < 0. A positive coefficient is unphysical. |

When a parameter is clamped at its bound, its posterior standard deviation is
reported as 0.0 (parameter is not free). To add or modify bounds, edit the
`_PHYSICAL_PARAM_BOUNDS` dict in `src/codameter/workflow.py`.

---

## Citing

If you use `codameter` in published work, please cite both the framework
paper and the software:

```bibtex
@article{Denolle2026,
  author = {Denolle, M. A.},
  title  = {{Relative seismic velocity changes as coupled stress and strain meters: a unified framework}},
  journal = {Journal of Geophysical Research: Solid Earth},
  year   = {2026},
  note   = {in prep}
}

@software{codameter,
  author = {Denolle, M. A. and the GAIA HazLab},
  title  = {codameter: An operational pipeline for interpreting seismic velocity changes},
  year   = {2026},
  doi    = {10.5281/zenodo.XXXXXXX},
  url    = {https://github.com/Denolle-Lab/codameter}
}
```

A `CITATION.cff` is provided in the repo root.

---

## License

MIT — see [`LICENSE`](LICENSE).

## Acknowledgements

This package builds directly on the open-source ecosystem of the seismology
community: [`disba`](https://github.com/keurfonluu/disba) (Luu, 2021) for
surface-wave eigenmodes, `emcee` (Foreman-Mackey et al., 2013) for MCMC,
`xarray`, `pandas`, `pyarrow`, `numpy`, and `scipy`. The empirical models
implemented here are due to Berger (1975), Roeloffs (1988), Talwani et al.
(2007), Snieder et al. (2017), Fokker et al. (2021), Okubo et al. (2024),
Clements & Denolle (2023), Ermert et al. (2023), Tromp & Trampert (2018), and
Shi et al. (2026), among others.
