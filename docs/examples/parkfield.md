# Synthetic Parkfield walkthrough

This example generates 10 years of synthetic dv/v from the forward
models that the workflow inverts, then runs the full six-phase pipeline
and verifies that the truth amplitudes are recovered. It is the
canonical sanity check for a fresh install.

## What the synthetic contains

- A 50-day-lagged thermoelastic response to surface temperature
  (annual cosine + daily noise).
- Groundwater-level proxy from log-normal-storm precipitation, fed
  through the Okubo et al. (2024) exponential-decay GWL model.
- A single coseismic event at year 4 with logarithmic Snieder healing.
- 1.5 × 10⁻⁴ white noise.

## Running

```bash
python examples/01_parkfield_synthetic.py --output runs/parkfield/
```

## Expected result

| Parameter | Truth | Recovered | z |
|---|---|---|---|
| `p1_dGWL` | −3.0 × 10⁻³ | −3.000 × 10⁻³ ± 4.5 × 10⁻⁸ | −1.08 |
| `p2_T` | +8.0 × 10⁻⁵ | +7.991 × 10⁻⁵ ± 5.1 × 10⁻⁷ | −0.18 |

Reduced χ² = 1.01 (by construction, since we know the noise σ exactly).

## What each phase contributed

**Phase 0** found 0 outliers and 0 gaps. **Phase 1** at $f_c = 1.04$ Hz
returns peak depth ≈ 385 m with $\mu = 3.2$ GPa, $K = 9.5$ GPa.
**Phase 2** Tier 1 diagnosed Pe = 213 — drained regime, well-separated
from $\sim 1$, no coupling escalation. **Phase 3** built a 4-column
design (intercept + GWL + T + EQ-healing). **Phase 4** WLS recovered
the parameters within 1.1 σ. **Phase 5** found the residuals white
(p = 0.275). **Phase 6** estimated
$d(\delta v / v) / dp = -3.06 \times 10^{-7}$ Pa⁻¹.

## Modifying the example

The `make_synthetic()` function in
`examples/01_parkfield_synthetic.py` exposes the truth amplitudes
explicitly. Change them and re-run to see how the recovery scales —
this is a useful sanity check before you trust the inversion on your
own data.

To replicate the actual Parkfield (real data):

1. Acquire a parquet of Parkfield HRSN dv/v (e.g., from the
   companion [`dvv-coupled`][dvv-coupled] repository).
2. Use `examples/configs/parkfield.yaml` as the site config.
3. Provide PRISM temperature and precipitation extracted at the
   array centre.
4. Build a regional earthquake catalog (e.g., NCEDC) within 50 km.

[dvv-coupled]: https://github.com/Denolle-Lab/dvv-coupled
