# Golden datasets

Seeded synthetic CCF suites with known ground-truth dv/v(t), organised as a
**graded benchmark**: 30 cases, 10 per difficulty grade, spanning the monitoring
applications. Two consumers: the pytest regression oracle
(`tests/test_golden.py`) and this advisor's live validation.

## Layout

- `tests/data/golden/manifest.json`: the committed oracle: one entry per case
  with its recipe (grade, use case, motif, snr, seed, channels, decorr) and the
  frozen expected metrics (baseline-aligned RMS). Version-controlled.
- `tests/data/golden/cache/*.npz`: the regenerated arrays. Deterministic from
  the seed, so they are gitignored, not committed.
- `codameter.golden`: the generator. `CASES` is the recipe list; `generate(id)`
  rebuilds arrays; `recover(d, cfg, eps)` runs the pipeline (aggregating channels
  for multi-channel cases); `regenerate_manifest()` recomputes expected metrics.

## The grades

Case ids are `{grade}-{application}-{nn}`, e.g. `easy-volcano-01`,
`hard-groundwater-08`. Each grade cycles through the applications (volcano,
earthquake/fault, landslide, groundwater, cryosphere, geothermal).

- **easy** (split `validation`): a pure seasonal signal at high SNR (8-12),
  single channel. Best-practice recovery should be well under 0.2 % RMS.
- **medium** (split `validation`): a transient coseismic-style drop with
  logarithmic partial healing, plus more measurement noise (SNR 3-5).
- **hard** (split `test`): a **multi-channel** (4-channel) *and*
  **depth/frequency-dependent** problem. A shallow (high-frequency) layer carries
  a coseismic drop-and-heal plus a full hydrological seasonal cycle; a deep
  (low-frequency) layer carries a long-term trend. Each case targets one depth
  (`target: shallow|deep`), so the measurement **band selects the depth** and must
  match the target. Low SNR (2-4) with waveform decorrelation; channels are
  measured independently and aggregated (`golden.recover`).

The benchmark therefore grades estimator, reference, stacking, aggregation *and*
depth-band selection: on a hard case, a band that recovers the wrong layer scores
near zero (the "clearly wrong" anchor is the wrong-layer error,
`expected.rms_wrong_layer`).

## Inspect

```bash
pixi run python -c "
import json
m = json.load(open('tests/data/golden/manifest.json'))
for c in m['cases']:
    print(f\"{c['id']:<26} {c['grade']:<7} ch={c['channels']} rms={c['expected']['rms']:.5f}\")"
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
