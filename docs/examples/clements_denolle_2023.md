# Clements & Denolle (2023) — running the workflow on the real archive

The script `examples/02_clements_denolle_2023.py` is the canonical
harness for testing `codameter` against

> Clements, T. & Denolle, M. A. (2023). The seismic signature of
> California's earthquakes, droughts, and floods.
> *J. Geophys. Res. Solid Earth*, **128**, e2022JB025553.
> [doi:10.1029/2022JB025553](https://doi.org/10.1029/2022JB025553)

The data products live at <https://doi.org/10.5281/zenodo.6413275>
(4.4 GB), and the original Julia code is at
<https://github.com/Denolle-Lab/Clements-Denolle-2022>.

## Two operating modes

### Synthetic mode (no download, ~30 s)

```bash
python examples/02_clements_denolle_2023.py --output runs/cd_synthetic/
```

The script writes a small fake archive that mimics the upstream
Zenodo layout (`DVV/{station}.feather` + `meteorology/{station}_P.csv`
+ `meteorology/{station}_T.csv`), points the C&D loader at it, and
runs the workflow. Truth amplitudes for the synthetic model are
recovered to within a fraction of a sigma. This is the test you run
*before* committing to the 4.4 GB download.

### Real-data mode

After unpacking the Zenodo archive:

```bash
python examples/02_clements_denolle_2023.py \
    --data-dir /scratch/cd2023/ \
    --station  CI.LJR \
    --precip   /scratch/cd2023/meteorology/LJR_P.csv \
    --temp     /scratch/cd2023/meteorology/LJR_T.csv \
    --config   examples/configs/clements_denolle_2023_LJR.yaml \
    --output   runs/CI_LJR/
```

The C&D loader auto-detects three on-disk layouts that the upstream
archive has used over its history:

1. `{data_dir}/DVV/{station}.feather`  (current Zenodo layout)
2. `{data_dir}/DVV/{station}.arrow`    (older Julia output)
3. `{data_dir}/{station}.parquet`      (post-conversion to parquet)

If you have the raw `.arrow` files and want to convert them to
parquet for downstream tooling:

```python
import pandas as pd
from pathlib import Path

for arrow in Path("DVV").glob("*.arrow"):
    pd.read_feather(arrow).to_parquet(arrow.with_suffix(".parquet"))
```

## The CI.LJR canonical case

CI.LJR (La Jolla Arroyo, San Gabriel Basin) is the type-locality
example of §5.3.1 of C&D 2023 — the 2004-05 Southern California winter
in which 11 atmospheric rivers raised groundwater 20 m and dropped
the dv/v by >1 %. The packaged config
`examples/configs/clements_denolle_2023_LJR.yaml` reproduces that
inversion at the workflow level: a hydrological + thermoelastic
linear superposition with the C&D priors.

## What you get

Per the standard `WorkflowResult.export()` contract:

| Artifact | Contents |
|---|---|
| `summary.txt` | Six-phase text summary |
| `results.json` | Phase-by-phase JSON |
| `parameters.csv` | Fitted parameters with 95 % CIs |
| `residuals.csv` | Observed, fitted, residual, σ |
| `diagnostic.png` | Six-panel diagnostic figure |
| `recovery.json` | (synthetic mode only) truth-vs-fit comparison |

## Comparing with the C&D 2023 published numbers

Two parameters are directly comparable:

- **`p1_dGWL`** — the hydrological coefficient, units fraction / m of GWL.
  This is the negative of C&D 2023's $a_2 \cdot S_{sk} \beta / B$
  (their Eq. 18-20 sign convention is opposite to ours).
- **`p2_T`** — the thermoelastic coefficient, units fraction / °C.
  Comparable to C&D 2023's $a_1$.

The mixing ratio $R_T = p_2 / (p_1 + p_2)$ from C&D 2023 Figure 4 can
be reconstructed from the `parameters.csv` output. Note units of
`p1_dGWL` and `p2_T` are different (the former is per metre of GWL,
the latter per °C), so always compute the contributions in dv/v space
before forming the ratio.

## Caveats

- The PRISM extraction at each station is not part of `codameter`
  — use the upstream Julia tooling (`PRISMgetscript.jl` /
  `bil2netcdf.jl`) or any other GIS workflow to produce the per-station
  CSVs. The harness expects daily precipitation (m) and daily air
  temperature (°C).
- `codameter` v0.1 uses the Okubo et al. (2024) exponential-decay
  GWL proxy by default, **not** the Roeloffs (1988) drained term that
  C&D 2023 used at most sites. To reproduce the C&D 2023 fit
  exactly, set the `hydrological.model: roeloffs1988` field in the
  YAML (and provide a `diffusivity` prior); a fully aligned
  reproduction config is on the v0.2 roadmap.
- The dv/v sign in the upstream feather is *percent*; the loader
  converts to fraction internally. If you see absolute values >0.1
  in the loader output, you're seeing percent — which means the
  upstream file is not the standard archive format.
