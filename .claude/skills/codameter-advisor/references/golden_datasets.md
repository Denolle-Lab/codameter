# Golden datasets

Seeded synthetic CCF suites with known ground-truth dv/v(t), covering the
mainstream per-application cases and four edge regimes. Two consumers: the pytest
regression oracle (`tests/test_golden.py`) and this advisor's live validation.

## Layout

- `tests/data/golden/manifest.json`: the committed oracle: one entry per case
  with its recipe (use case, years, snr, seed, cadence, decorr) and the frozen
  expected metrics (baseline-aligned RMS, plus any probes). Version-controlled.
- `tests/data/golden/cache/*.npz`: the regenerated arrays. Deterministic from
  the seed, so they are gitignored, not committed.
- `codameter.golden`: the generator. `CASES` is the recipe list; `generate(id)`
  rebuilds arrays; `regenerate_manifest()` recomputes the expected metrics.

## The cases

Mainstream (one per application): `volcano_mainstream`, `earthquake_mainstream`,
`landslide_mainstream`, `groundwater_mainstream`, `cryosphere_mainstream`,
`geothermal_mainstream`. Each should recover its truth to well under 0.2 % RMS.

Edge:
- `low_snr_large_dvv`: SNR ~2 with a several-percent pre-failure drop; the
  cycle-skipping regime that splits stretching from cross-spectral methods.
- `clock_drift_seasonal`: a growing clock error plus a seasonal late-coda warp;
  injects a spurious dv/v (Zhan 2013 / Daskalakis 2016).
- `freqdep_shallow_deep`: shallow (high-freq) and deep (low-freq) layers carry
  different dv/v; the band selects which one you recover. Has a probe proving the
  deep band recovers the deep layer.
- `sparse_decorr`: every-third-day sampling with 30 % waveform decorrelation;
  stresses the reference and stacking warm-up.

## Inspect

```bash
pixi run python -c "
import json
m = json.load(open('tests/data/golden/manifest.json'))
for c in m['cases']:
    print(f\"{c['id']:<24} {c['kind']:<10} rms={c['expected']['rms']:.5f}\")"
```

## Add or change a case

1. Append a recipe dict to `codameter.golden.CASES` (see the docstring there for
   the fields). Reuse the synthesis geometry from `codameter.use_cases` via the
   `use_case` key; only add a new ground-truth generator in `golden.TRUTH` if no
   existing one fits.
2. Regenerate the oracle: `pixi run golden`. Review the printed RMS values; they
   should be small for a recovery case and a stable non-zero value for an
   artifact case.
3. Lock it in: `pixi run -e test pytest tests/test_golden.py -q`.
4. Commit `manifest.json` only. Never commit the `.npz` cache.

If a genuine estimator improvement shifts an RMS beyond its `rms_rel_tol`,
regenerate the manifest in the same commit and note why in the message. The
tolerance is a drift guard, not a target.

## FrugalMind benchmark view

The same cases are exposed as a FrugalMind benchmark through
`codameter.frugalmind`: `build_rows(task)` emits `BenchmarkRow`-shaped dicts and
`make_scorer_from_spec` returns the deterministic scorers. Two tasks:
`param_recommendation` (agent returns a config; scored by dv/v recovery via
`run_pipeline`) and `dvv_series` (agent returns the recovered dv/v(t); scored by
regression vs truth). Export with `pixi run frugalmind-export`; the drop-in
suite is in `integrations/frugalmind/`. Adding or changing a golden case updates
the FrugalMind rows automatically, since both read `golden.CASES`.
