# Data Requirements

Most users start with one CSV or Parquet file containing a dv/v time series.
That is enough to check data quality and run exploratory fits, but it is not
enough to claim groundwater change, stress at depth, or a specific coupling
mechanism. Use `data-check` before a run:

```bash
codameter data-check \
  --dvv my_dvv.parquet \
  --config site.yaml \
  --goal groundwater \
  --goal stress \
  --precip precipitation.csv \
  --temp temperature.csv
```

The command reads CSV, TSV, Parquet, Feather, and Arrow inputs. By default it
prints a report and exits 0. Add `--fail-on-missing` when using it in CI or a
batch-processing script.

## Minimum dv/v file

Your dv/v file should have:

| Column | Required | Notes |
|---|---:|---|
| `time` / `date` / `datetime` | yes | Parsed as UTC and used as the index. |
| `dvv` | yes | Fraction by default; pass `--dvv-units percent` for percent. |
| `dvv_err` | strongly yes | Needed for defensible WLS weights and uncertainty propagation. |
| `cc` or `correlation_coefficient` | recommended | Keeps quality-control decisions auditable. |

If `dvv_err` is absent, `load_dvv()` fills `0.001` so the workflow can run.
The readiness report still flags this as missing scientific information.

## Goal 1: Groundwater Or Soil-Moisture Monitoring

Minimum useful inputs:

| Input | Why it matters |
|---|---|
| Site YAML with location, measurement band, and velocity model | Sets the depth range and physical scale. |
| Precipitation, snowmelt/SWE, groundwater level, soil moisture, streamflow, GRACE, or a precomputed storage proxy | Supplies the hydrologic driver or proxy. |
| `dvv_err` | Required for meaningful uncertainty on fitted hydrologic sensitivity. |

Add next:

| Data to add | What it unlocks |
|---|---|
| Well level, pore pressure, or in-situ soil moisture | Calibration from relative dv/v proxy to physical water storage. |
| Temperature | Separates thermoelastic seasonality from hydrologic seasonality. |
| Snowpack/SWE and evapotranspiration where relevant | Reduces false hydrologic attribution in snow-dominated or arid sites. |

Interpretation rule: precipitation plus dv/v supports a relative storage
proxy. Absolute groundwater depth or soil moisture needs independent
hydrologic calibration.

## Goal 2: Stress Inversion At Depth

Minimum useful inputs:

| Input | Why it matters |
|---|---|
| Velocity model and measurement frequency band | Determines the sensitivity depth. |
| Material-property priors or estimates | Needed for beta, mu_prime, porosity, Skempton B, and hydraulic diffusivity. |
| Calibrated pressure/loading/strain constraint | Needed to turn fitted coefficients into stress, not only correlation. |
| Environmental forcings | Remove shallow hydrologic and thermoelastic terms before interpreting residual stress. |

Add next:

| Data to add | What it unlocks |
|---|---|
| Multiple frequency bands or station pairs | Tests whether the inferred stress is depth-localized. |
| GNSS, strainmeter, barometric/tidal loading, or well-pressure data | Independent calibration of stress/strain sensitivity. |
| Logs, UCVM, Vs30, or literature property ranges | Reduces prior-dominated stress estimates. |

Interpretation rule: stress-at-depth estimates are only as good as the kernel
depth, elastic moduli, and the calibration of the fitted forcing coefficient.

## Goal 3: Coupling-Mechanism Identification

Minimum useful inputs:

| Input | Why it matters |
|---|---|
| At least two forcing families | Needed to distinguish hydrologic, thermal, loading, and damage mechanisms. |
| Earthquake catalog when testing damage/healing | Supplies event times and magnitude/location context. |
| Site YAML and velocity model | Needed for Tier 1 drainage and depth diagnostics. |

Add next:

| Data to add | What it unlocks |
|---|---|
| Surface-load data: SWE, barometric pressure, tides, modeled water load | Separates loading from pore-pressure diffusion. |
| Independent hydrologic/strain observations | Validates the preferred mechanism outside dv/v. |
| Multiple components, station pairs, or frequency bands | Tests spatial and depth coherence of residual patterns. |

Interpretation rule: mechanism identification is model selection. Residual
whiteness is useful, but not sufficient without independent forcing data.

## Python API

```python
from codameter import assess_data_readiness, load_site
from codameter.data import load_dvv, load_timeseries

site = load_site("site.yaml")
dvv = load_dvv("my_dvv.parquet")
forcings = {
    "precipitation": load_timeseries("precipitation.parquet"),
    "temperature": load_timeseries("temperature.csv"),
}

report = assess_data_readiness(
    dvv,
    site=site,
    forcings=forcings,
    goals=["groundwater", "stress", "coupling"],
)
print(report.to_text())
```
