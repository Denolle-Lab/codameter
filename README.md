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
