# Use-case elicitation

Goal: establish the application and, where the user knows them, the fields that
change a parameter axis. The question set is `codameter.use_cases.ELICITATION`;
read it live rather than hardcoding it here:

```bash
pixi run python -c "
import json
from codameter import use_cases as uc
print(json.dumps(uc.ELICITATION, indent=2, default=str))"
```

## How to ask

Batch the questions with `AskUserQuestion`. The only field you must resolve is
**application**. Everything else has a use-case default, so treat it as optional
enrichment. Do not interrogate a user who already gave you what you need.

If the user described their problem in free text, infer the application first and
confirm it rather than asking cold:

```bash
pixi run python -c "from codameter import use_cases as uc; print(uc.resolve('shallow rock-glacier permafrost site'))"
# -> cryosphere
```

## What each answer changes (`maps_to`)

| Field | Overrides |
| --- | --- |
| application | the whole config, via `recommend(application)` |
| target_process | `stack` (short for a transient, long for a trend) and `reference` (a monotonic trend wants `fixed` or `inversion`, never `moving`) |
| frequency | `band` (only override the default if the user names a specific range) |
| geometry | aggregation and the minimum usable lapse (single-station autocorr wants an earlier, shorter window than distant pairs) |
| amplitude | `estimator` and `eps_max` (dv/v above ~1 % cycle-skips cross-spectral methods; widen the stretching search) |
| cadence | `stack` length |
| noise | safeguards: clock error -> check the causal/acausal branch split; non-stationary sources -> restrict the band and keep `gate=True`; low SNR -> prefer stretching, keep gating; gaps -> expect a warm-up mask |

## Also capture: the user's current choices

Ask what they use now (band, window, estimator, reference), if anything. Step 3
compares the recommendation against this. If they have no current pipeline, Step
3 compares against a deliberately naive config (for example a `moving` reference
or an off-target band) to show the size of the effect.
