# The six-phase workflow

`codameter` is built around the operational workflow of §12 of *Denolle
(in prep, JGR Solid Earth)*. Each phase is a self-contained step with
typed inputs, a typed result object, and side-effect-free execution.
The orchestrator `run_workflow()` wires them together; you can also
call each phase directly.

The workflow is **not a pipeline but a loop**. Each phase may trigger a
return to an earlier phase (see *Iteration* below).

---

## Phase 0 — Data ingestion + QC

**Input:** raw $\delta v / v$ (parquet / CSV / feather) plus optional
forcing time series.

**Computation:** type coercion, outlier flagging (default 6σ), gap
detection, time-axis alignment of forcings to the $\delta v / v$ index.

**Output:** `Phase0Result` containing aligned forcings, a quality
report, and the cleaned dv/v Series.

The QC step is deliberately mild — it flags rather than imputes. If you
need imputation, do it upstream and feed clean data in.

---

## Phase 1 — Site characterisation

**Input:** the layered velocity model from the YAML config and the
measurement frequency band.

**Computation:** if `disba` is installed and `mode='kernel'`, compute
the Rayleigh-wave depth-sensitivity kernel and integrate to find the
peak-sensitivity depth. Otherwise fall back to the
$z_{\text{peak}} \approx V_S / (3f)$ rule of thumb (Hillers et al.,
2015).

**Output:** depth-frequency table, peak depth at the central frequency,
shear and bulk modulus at that depth.

The peak depth feeds Phase 2 (as the diffusion length scale) and
Phase 6 (as the depth at which stress sensitivity is reported).

---

## Phase 2 — Coupling diagnostics (Tier 1)

**Input:** Phase 1 peak depth + the material-property priors from the
YAML.

**Computation:** the drainage Péclet number
$\mathrm{Pe}_d = T_{\text{forc}} / (L^2 / c)$ at the dominant forcing
period, plus the frequency-dependent $\beta_{\text{eff}}(\omega)$
from Eq. 15 of *Denolle (in prep)*.

**Output:** `CouplingReport` with the Tier 1 numbers and an escalation
flag. Two-tier thresholds (configurable):

- $\mathrm{Pe}_d \in [0.3, 3]$ → soft warning
- $\mathrm{Pe}_d \in [0.1, 10]$ → hard escalate

**If escalate=True** the linear-superposition assumption (Eq. 6) is
violated; the v0.1 workflow still runs the linear fit but flags it,
and v0.2 will route to the coupled MCMC inversion.

Tiers 2, 3, 4 stubs exist; full implementations are scheduled for v0.3.

---

## Phase 3 — Linear-superposition design matrix

**Input:** aligned forcings from Phase 0.

**Computation:** for each enabled forcing, build one column of the
predictor matrix

$$
\frac{\delta v}{v}(t) = a_0 + p_1 \Delta GWL(t) + p_2 T(t - t_{\text{shift}})
                       + \sum_i s_i L(t, \tau_{\min}, \tau_{\max}, t_{EQ,i}).
$$

The hydrological column uses the Okubo et al. (2024) GWL proxy; the
thermoelastic column uses the Okubo phase-shift form (or Berger
skin-depth diffusion via the function-level API); the damage columns
use Snieder healing.

**Output:** `PredictorMatrix` with the design, parameter names, units,
and the metadata on which choices were made.

---

## Phase 4 — Linear inversion (WLS)

**Input:** Phase 0 dv/v + measurement uncertainty + Phase 3 design.

**Computation:** weighted least squares with closed-form Gaussian
posterior. NaN/inf rows are dropped. Reduced χ² is reported.

**Output:** `LinearFitResult` with fitted means, full covariance,
residuals, and a tidy `summary()` DataFrame.

The full coupled (state-dependent) inversion of Eq. 21 is deferred to
v0.2.

---

## Phase 5 — Anomaly detection

**Input:** Phase 4 residuals.

**Computation:** Ljung–Box whiteness test (default 30 lags), rolling
z-score transient detection, and a structured anomaly report.

**Output:** `AnomalyReport` containing the whiteness p-value, transient
segments, and a dict serialisable to JSON.

If the residuals are not white, you have evidence of unmodelled
physics. The next step is to return to Phase 2 (was a coupling tier
underestimated?), then Phase 1 (is the velocity model wrong?), then
Phase 0 (is there a data quality issue?). This is the iterative loop
referred to above.

---

## Phase 6 — Interpretation

**Input:** Phase 1 moduli + Phase 4 fitted hydrological coefficient.

**Computation:**

1. Convert the fitted $p_1$ (units fraction / metre of GWL) to a
   pressure sensitivity $d(\delta v / v) / dp$ by dividing by $\rho g$.
2. Multiply by the bulk modulus to get $\beta_{\text{eff}}$, the
   effective acoustoelastic coefficient that the data supports.
3. Use the bridge relation $\beta = -\mu' \kappa / 2\mu$ to back out
   $\mu'$, the nonlinear-elasticity sensitivity.
4. Propagate uncertainties through every step.

**Output:** `Phase6Result` with `pressure_sensitivity`,
`mu_prime_estimate`, and a list of human-readable notes.

The water-table-depth and saturation inversion (Eqs. 20–22 of the
manuscript) is scheduled for v0.2.

---

## Iteration: the workflow as a loop

Per §12 of the manuscript, residuals from Phase 5 should drive
re-entry into earlier phases:

| Residual diagnostic | Likely culprit | Re-enter |
|---|---|---|
| Systematic seasonality | Incomplete environmental model | Phase 4 |
| Frequency-dependent structure | Wrong velocity profile or kernel | Phase 1 |
| Non-stationarity around earthquakes | Tier 2 underestimated | Phase 2 |
| Interannual variability tracking drought indices | Tier 3 underestimated | Phase 2 |
| Small white residuals + persistent long-term trend | Tectonic / volcanic anomaly | Phase 6 (interpret) |

The convergence of the loop is the point at which adding model
complexity no longer improves the fit — formalised via AIC, BIC, or
posterior predictive checks (v0.2+).
