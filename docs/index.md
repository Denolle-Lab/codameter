# codameter

**An operational six-phase workflow for interpreting relative seismic velocity
changes ($\delta v / v$) as stress and strain meters.**

`codameter` is the executable companion to *Denolle (in prep, JGR Solid
Earth)*. Given a $\delta v / v$ time series and the relevant environmental
forcings (temperature, precipitation, earthquake catalog, ...), the package
extracts:

- depth-resolved stress estimates with propagated uncertainties,
- water-table-depth and saturation inversions (v0.2+),
- coupling-tier diagnostics that flag when linear superposition fails,
- anomaly classifications (tectonic, volcanic, hydrological, post-seismic,
  anthropogenic) for residual signal not explained by the physical model.

It is the operational tool any group can apply to their own data; the
manuscript-companion repository [`dvv-coupled`][dvv-coupled] generates
the JGR figures.

[dvv-coupled]: https://github.com/Denolle-Lab/dvv-coupled

## At a glance

```python
from codameter import run_workflow, load_site
from codameter.data.loaders import load_dvv, load_csv_timeseries

site = load_site("parkfield.yaml")
dvv  = load_dvv("parkfield.parquet")
forc = {
    "temperature":   load_csv_timeseries("T.csv"),
    "precipitation": load_csv_timeseries("P.csv"),
}

result = run_workflow(dvv, forc, site)
print(result.summary())
result.export("parkfield_run/")
```

## Status — v0.1

| Phase | What it does | v0.1 |
|---|---|---|
| 0 | Data ingestion + QC | ✅ |
| 1 | Site characterisation; depth-frequency table | ✅ |
| 2 | Coupling diagnostics — Tier 1 (poroelastic) | ✅ |
|   | Tiers 2 (damage–permeability), 3 (saturation), 4 (thermo-capillary) | v0.3+ |
| 3 | Linear-superposition design matrix (Eq. 6) | ✅ |
| 4 | Linear inversion (WLS) | ✅ |
|   | Coupled inversion (MCMC) | v0.2 |
| 5 | Anomaly detection | ✅ |
| 6 | β-bridge stress at depth | ✅ |
|   | Water-table inversion | v0.2 |

See [the changelog](changelog.md) and [known issues](known_issues.md) for
details.

## Where next

- **Just installed?** → [Quickstart](quickstart.md)
- **Want the conceptual picture?** → [The six-phase workflow](workflow.md)
- **Want the math?** → [Theory pointer](theory.md)
- **Want a runnable example?** → [Parkfield synthetic](examples/parkfield.md)
  or [Clements & Denolle 2023 harness](examples/clements_denolle_2023.md)

## Citing

Please cite both:

```bibtex
@article{Denolle2026dvv,
  title  = {Seismic Velocity Changes as Stress and Strain Meters: A Unified Framework for Forcing, Coupling, and Inversion},
  author = {Denolle, Marine A.},
  journal = {Journal of Geophysical Research: Solid Earth},
  year   = {2026},
  note   = {in preparation}
}

@software{codameter_2026,
  title  = {codameter: Operational pipeline for interpreting seismic velocity changes as stress and strain meters},
  author = {Denolle, Marine A.},
  year   = {2026},
  doi    = {10.5281/zenodo.PLACEHOLDER},
  url    = {https://github.com/Denolle-Lab/codameter}
}
```
