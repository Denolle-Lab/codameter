# Live synthetic assessment

Use public development scenarios for advice. Synthetic recovery measures
performance conditional on the imposed truth, waveform, noise, and choices.
It does not prove a recommendation for field observations.

## Recommended versus comparison

`golden.advisory_case` builds a seasonal example for every application.
It does not depend on `MAINSTREAM_BY_USE_CASE` or private cases.
The returned recipe records the seed, duration, application, and noise.
Application defaults share assumptions with the generator. This is a
consistency check, not an independent generalization benchmark.

```python
import numpy as np
from codameter import use_cases as uc, golden

key = uc.resolve("volcano")
user_overrides = {"reference": "moving"}
d = golden.advisory_case(key, seed=101)
rec = uc.recommend(key)
usr = uc.recommend(key, **user_overrides)
eps = uc.eps_max(key)
support = golden.scoring_support(d, rec, eps)
print("scenario:", d["recipe"])
for label, cfg in [("recommended", rec), ("comparison", usr)]:
    dvv, valid = golden.recover(d, cfg, eps)
    prediction = np.where(valid, dvv, np.nan)
    rms, availability = golden.rms_on_support(prediction, d["truth"], **support)
    print(label, cfg, "RMS [%]", rms * 100, "availability", availability)
```

`recover` measures each channel before averaging multi-channel cases.
Both configurations use the reference configuration's fixed epochs and datum.
Missing predictions on that support count as zero baseline-relative change.
Report availability separately. Selective abstention can still improve a poor
prediction; the score is not evidence of complete temporal recovery.
A non-finite RMS means the comparison lacks a usable datum.

For a named public evaluation case, inspect `golden.CASES_BY_ID` first.
Apply the recipe's `config` overrides before creating the reference config.
A hard groundwater case targets a particular frequency component; its band
is not the generic groundwater default. Never open private evaluation data
for routine advice or display scorer truth to an evaluated agent.

## Interpret the comparison

Report RMS in percent, the difference, and both availabilities.
Do not call choices equivalent because their RMS values differ by 20 percent.
Repeated independent waveform/noise realizations are needed to quantify the
uncertainty of that difference. Record all seeds and settings when repeating.
The default example is seasonal; transient recovery requires a stated
transient scenario, not a claim inferred from the seasonal run.
A trailing reference without accumulation measures a different temporal
quantity. Label that comparison as an ablation.

The six pipeline axes are executable overrides. Other elicited properties
are context until explicitly encoded in the generator. State unmodeled
geometry, target depth, forcings, SNR, artifacts, and gaps.

## Optional factorial and covariance

`codameter.deviations.multiverse` uses the volcano scenario. Its sensitivity
ranking is conditional on that waveform and sampled configuration menu.
Do not report it as an application-independent ranking or an attribution
across independent field observations.

`bayes_dvv_from_ccfs` accepts a complete daily CCF grid. It returns a model
posterior and a separately constructed single-member covariance `Cd`.
`mu_cov` describes the combined estimate under the conditional-independence
model. Neither object automatically captures shared artifacts. The locked
calibration reports poor credible-band coverage on the combined estimate.
A single-member `Cd` is not a calibrated covariance of that estimate or a
cross-band covariance for depth inversion. Explain these distinctions before
using either object downstream. Report standard deviations in fractional
dv/v or percent explicitly; covariance units are fractional dv/v squared.
