# Quickstart

Five minutes from clone to first plot. We use the Parkfield synthetic
example because it has no external dependencies.

## 1. Install

```bash
git clone https://github.com/Denolle-Lab/codameter.git
cd codameter
pip install -e .
```

## 2. Run the synthetic Parkfield demo

```bash
python examples/01_parkfield_synthetic.py --output runs/quickstart/
```

Expected output (abridged):

```
[step 1/3] generating 10 years of synthetic Parkfield data...
[step 2/3] running six-phase workflow...

=== codameter result for site 'parkfield_synthetic' ===

Phase 0  Data:    n=3650 samples, outliers=0
Phase 1  Kernel:  fc=1.04 Hz -> peak depth = 385 m  (mu=3.2 GPa, K=9.5 GPa)
Phase 2  Coupling: Pe=213.01 -> safe; escalate=False
Phase 3  Design:  forcings=['hydrological', 'thermoelastic', 'damage'], n_par=4
Phase 4  Fit:     chi2_red=1.01, rank=4/4
           a0       = -6.7e-06 ± 3.5e-06
           p1_dGWL  = -3.0e-03 ± 4.5e-08
           p2_T     = +8.0e-05 ± 5.1e-07
           s_eq_... = -2.0e-03 ± 1.8e-05
Phase 5  Anomaly: whiteness p=0.275, transients=0
Phase 6  Interp:  d(dv/v)/dp = -3.06e-07 ± 4.5e-12 1/Pa

[recovery]
  p1_dGWL    truth=-3.000e-03  fit=-3.000e-03 ± 4.45e-08  z=-1.08  [OK]
  p2_T       truth=+8.000e-05  fit=+7.991e-05 ± 5.12e-07  z=-0.18  [OK]

[OK] all parameters recovered within 4σ.
```

The artifacts in `runs/quickstart/` are:

| File | What it is |
|---|---|
| `summary.txt` | The full text summary above |
| `results.json` | Phase-by-phase results, machine-readable |
| `parameters.csv` | Fitted parameters with 95 % CIs |
| `residuals.csv` | Observed dv/v, fitted, residual, σ per sample |
| `diagnostic.png` | Six-panel diagnostic figure |

## 3. Validate a config

Before running, check a config with the pre-flight validator. It catches
unknown forcing models, inverted date ranges, and unsupported options
without executing the workflow:

```bash
codameter validate --config examples/configs/parkfield.yaml
```

A valid config prints a `✓` line listing the active forcings and exits 0;
problems are reported as a `⚠` list and exit non-zero, so it can be used as
a gate in scripts and CI.

## 4. Run on your own data

The high-level API takes three things: a `Site` (from a YAML config),
a dv/v DataFrame, and a forcings dict.

```python
from codameter import run_workflow, load_site
from codameter.data.loaders import load_dvv, load_csv_timeseries

site = load_site("examples/configs/parkfield.yaml")
dvv  = load_dvv("my_dvv.parquet")        # needs columns "dvv" and "dvv_err"
forc = {
    "temperature":   load_csv_timeseries("T.csv"),
    "precipitation": load_csv_timeseries("P.csv"),
}

result = run_workflow(dvv, forc, site)
print(result.summary())
result.export("runs/my_site/")
```

## 5. Run on Clements & Denolle (2023) data

Synthetic mode (no download needed):

```bash
python examples/02_clements_denolle_2023.py --output runs/cd_synthetic/
```

Real Zenodo data (after the 4.4 GB unpack):

```bash
python examples/02_clements_denolle_2023.py \
    --data-dir /scratch/cd2023/ \
    --station  CI.LJR \
    --precip   /scratch/cd2023/meteorology/LJR_P.csv \
    --temp     /scratch/cd2023/meteorology/LJR_T.csv \
    --config   examples/configs/clements_denolle_2023_LJR.yaml \
    --output   runs/CI_LJR/
```

## 6. Where next

- [The six-phase workflow](workflow.md) — what each phase does and why
- [Known issues](known_issues.md) — read this before publishing results
