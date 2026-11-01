# Golden datasets

Seeded synthetic CCF suites with known ground-truth dv/v(t), organised as a
**graded template family**: 30 templates, 10 per difficulty grade.
The checkout exposes three public cases, one per grade. A separately
provisioned corpus supplies private cases. Public examples are development
checks; no completed external-model evaluation is claimed. Two consumers: the pytest regression oracle
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
  **frequency-component selection** problem. A shallow (high-frequency) layer carries
  a coseismic drop-and-heal plus a full hydrological seasonal cycle; a deep
  (low-frequency) layer carries a long-term trend. Each case targets one depth
  (`target: shallow|deep`), so the measurement band selects the imposed component and must
  match the target. This separated-band surrogate does not validate physical
  depth resolution or kernels. Low SNR (2-4) with waveform decorrelation; channels are
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

1. Append a recipe dict to the explicit public recipe source or private corpus builder, as appropriate.
   `CASES` is populated when the module loads; it is not a persistent registry. Reuse the synthesis geometry from `codameter.use_cases` via the
   `use_case` key; only add a new ground-truth generator in `golden.MOTIF` if no
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

## Evaluation limits

Public templates and application defaults share construction assumptions.
Hidden amplitudes do not establish a holdout of waveform physics. Difficulty
and split are confounded in the current template family. Frozen RMS tolerances
are regression tolerances, not scientific accuracy requirements.

`observed()` removes truth keys from a dictionary; it is not a sandbox.
An evaluated agent must not access recipe files, truth caches, scorer metadata,
or generator routes that reconstruct the answer. Process and filesystem
isolation remain work for the evaluation harness. Scorer support is fixed per
case; missing predictions are scored as null change and availability is reported.
No model transcripts or validated agent-performance claims accompany this corpus.
