# Live validation

This is the step that makes the advice more than an opinion. Run the recommended
config and a comparison config on a matched synthetic with known ground truth,
and report the difference in bias and error bar. The truth is known exactly, so
every difference is an artifact of the processing choice, not of nature.

## The primitives

- `codameter.golden.generate(case_id)` returns `{ccfs, t, days, truth, fs, ...}`
  for a seeded case. `codameter.golden.MAINSTREAM_BY_USE_CASE[use_case]` gives a matched
  (easy-grade) case id for an application.
- `codameter.deviations.run_pipeline(ccfs, t, fs, cfg, eps_max=...)` returns
  `(dvv, valid)` for one config.
- `codameter.golden._rms(dvv, truth, days, valid)` is the baseline-aligned RMS
  error (removes the unobservable DC offset of a relative measurement).
- `codameter.deviations.multiverse(...)` returns the first-order variance
  attribution (volcano synthetic; use it for the "which choice controls the
  answer" statement).
- `codameter.uq_bayes.bayes_dvv_from_ccfs(ccfs, t, fs, truth=truth, days=days)`
  returns `(BayesResult, EnsembleRun)`; `BayesResult.Cd` is the marginal
  measurement covariance for a downstream inversion.

## Recommended vs comparison, on a matched synthetic

Fill `USER_CFG` with the user's current choices (or a deliberately naive config
if they have none). Run:

```bash
pixi run python - <<'PY'
from codameter import use_cases as uc, golden
from codameter.deviations import run_pipeline

USE_CASE = "volcano"                     # from Step 1
USER_CFG = {"reference": "moving"}       # the user's current choice(s), as overrides

key = uc.resolve(USE_CASE)
d = golden.generate(golden.MAINSTREAM_BY_USE_CASE[key])
eps = uc.eps_max(key)

rec = uc.recommend(key)
usr = uc.recommend(key, **USER_CFG)

for label, cfg in [("recommended", rec), ("user/naive", usr)]:
    dvv, valid = run_pipeline(d["ccfs"], d["t"], d["fs"], cfg, eps_max=eps)
    rms = golden._rms(dvv, d["truth"], d["days"], valid)
    print(f"{label:<12} {cfg}")
    print(f"{'':<12} RMS vs truth = {rms*100:.4f} %  (valid epochs {int(valid.sum())})")
PY
```

Report the two RMS values and the ratio. If the user's config is within ~20 % of
the recommended RMS, tell them their choice is fine; do not invent a penalty.

## Which choice controls the answer (volcano factorial)

For the ranking of axes by impact, run the one-at-a-time sweep or the multiverse:

```bash
pixi run python - <<'PY'
from codameter.deviations import multiverse
mv = multiverse(years=1.5, cadence=4)
print("pipelines:", mv["n_pipelines"])
for axis, frac in sorted(mv["sobol_rms"].items(), key=lambda kv: -(kv[1] or 0)):
    print(f"  {axis:<11} first-order variance share of RMS = {frac:.2f}")
PY
```

`multiverse` is wired to the volcano truth and geometry. For other applications,
report the OAT contrast from the recommended-vs-comparison run above rather than
claiming a full factorial you did not run.

## Optional: the marginal covariance C_d

For a user heading into a depth or stress inversion, show that the honest error
bar comes from marginalising the processing choice:

```bash
pixi run python - <<'PY'
from codameter import golden
from codameter.uq_bayes import bayes_dvv_from_ccfs
d = golden.generate("easy-volcano-01")
res, ens = bayes_dvv_from_ccfs(d["ccfs"], d["t"], d["fs"],
                               truth=d["truth"], days=d["days"], cadence=4)
import numpy as np
print("posterior median dv/v std:", float(np.nanmedian(np.sqrt(np.diag(res.Cd))))*100, "%")
PY
```

This is slower (it runs an ensemble of pipelines plus a Gibbs sampler); only run
it when the user cares about the propagated uncertainty, and say it is running.

## Reading the numbers honestly

- A lower RMS is better recovery; state the percentage, not an adjective.
- A `moving` reference erases the slow trend, so on a trend case it shows a large
  RMS by design. That is the point, not a bug.
- Harder cases (medium = transient + noise; hard = multi-channel composite)
  are in the golden manifest; pull one with `golden.generate("<grade>-<app>-<nn>")`
  when the user's situation is noisier or more complex than a clean seasonal one.
  Ids are in `golden.CASES_BY_ID`.
