# API reference

`codameter` exposes three usage tiers, each documented separately.

## High-level — one function call

```python
from codameter import run_workflow, load_site
```

→ [High-level API](high_level.md)

## Mid-level — phase by phase

```python
from codameter import Site, Phase0, Phase1, Phase2, Phase3, Phase4, Phase5, Phase6
```

→ [High-level API](high_level.md) (the Phase classes are documented there
  alongside `WorkflowResult`).

## Low-level — individual physics modules

```python
from codameter.forward.poroelastic import roeloffs_pressure_response
from codameter.forward.thermoelastic import berger_temperature_response
from codameter.forward.damage import snieder_healing
from codameter.coupling.tier1_poroelastic import drainage_peclet, frequency_dependent_beta_eff
from codameter.kernels.velocity_models import VelocityProfile, make_fine_model
from codameter.inverse.linear_fit import build_predictor_matrix, linear_fit
```

→ [Forward models](forward.md)
→ [Coupling diagnostics](coupling.md)
→ [Inversion](inverse.md)

## Stable vs experimental

| Module | Stability |
|---|---|
| `codameter.config` | stable |
| `codameter.workflow` | stable |
| `codameter.forward.{thermoelastic,poroelastic,damage}` | stable |
| `codameter.forward.{capillary,loading}` | experimental — physics in flux |
| `codameter.coupling.tier1_poroelastic` | stable |
| `codameter.coupling.{tier2,tier3,tier4}_*` | stub — v0.3+ |
| `codameter.inverse.linear_fit` | stable |
| `codameter.inverse.coupled_inversion` | stub — v0.2 |
| `codameter.interpretation.stress_at_depth` | stable |
| `codameter.interpretation.water_table` | stub — v0.2 |
| `codameter.kernels.disba_wrapper` | stable, optional |
| `codameter.kernels.depth_resolution` | stable |
| `codameter.data.loaders` | stable |
| `codameter.anomaly.detection` | stable |
| `codameter.anomaly.attribution` | experimental |

The "stable" modules will preserve their public signatures across
0.x releases unless flagged in the changelog.
