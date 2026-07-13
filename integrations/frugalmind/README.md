# FrugalMind integration: the dv/v processing suite

This directory is the adapter that turns codameter's golden dv/v datasets into a
[FrugalMind](https://github.com/mdenolle/frugalmind) benchmark suite. The domain
logic (synthetic generation, pipeline execution, scoring) stays in codameter
(`codameter.frugalmind`); the code here only wraps it in FrugalMind's
`DenolleGroupSuite` / `BenchmarkRow` contract, so neither repo hard-depends on
the other's internals.

## What it provides

Two suites under `dataset_id = "codameter"`, one per output type:

| suite_id | task_kind | model returns | scorer |
| --- | --- | --- | --- |
| `param_recommendation` | code_generation | a processing-choice config (JSON) | `dvv_recovery`: run the config on the hidden synthetic, grade recovery of the known dv/v |
| `dvv_series` | code_generation | the recovered dv/v(t) series (JSON array) | `dvv_series_regression`: regress against the known truth, anchored so a no-change series scores ~0 |

Both score in `[0, 1]` by recovery against ground truth (not by matching a fixed
answer), so a different-but-sound pipeline scores well and a wrong band or a
cycle-skipping estimator scores near zero. Ten cases per suite: six mainstream
(one per application) on the `validation` split, four edge regimes on `test`.

## Install into FrugalMind

1. Copy the `dvv/` package into the FrugalMind checkout:

   ```bash
   cp -r integrations/frugalmind/dvv <frugalmind>/src/frugalmind_suites/dvv
   ```

2. Add codameter to FrugalMind's environment (it is the scoring backend):

   ```bash
   pip install codameter        # or add to frugalmind's pixi/pyproject deps
   ```

3. Use it like any other suite:

   ```python
   import frugalmind as F
   from frugalmind_suites.dvv import ALL_SUITES

   F.load_env_keys()
   reg = F.ModelRegistry()
   runner = F.EvalRunner(registry=reg, suites=ALL_SUITES,
                         per_model_budget_usd=0.50, total_budget_usd=5.00)
   ```

4. Export the frozen JSONL through FrugalMind's standard exporter:

   ```bash
   pixi run export-suite --suite codameter.param_recommendation --out datasets/
   ```

   FrugalMind's `export_rows()` and codameter's own `export_jsonl` (below)
   produce the same rows.

## Self-hosted export (no FrugalMind needed)

codameter can also write the canonical JSONL layout directly, for CI or a
HuggingFace mirror:

```bash
pixi run frugalmind-export --out datasets/
# -> datasets/codameter/v0.1/{param_recommendation,dvv_series}.jsonl + manifest.json
```

## Notes

- The scorers regenerate the hidden synthetic from its seed and run the codameter
  pipeline, so scoring requires `codameter` importable (as sta_lta's code scorer
  requires ObsPy). The `gold` payload carries only `case_id` + tolerances, never
  the arrays, so the JSONL stays small and leak-free.
- Contract verified against `frugalmind` `DenolleGroupSuite` /
  `frugalmind.export.BenchmarkRow` / the family `make_scorer_from_spec` pattern.
  Run FrugalMind's own suite smoke tests after copying in.
