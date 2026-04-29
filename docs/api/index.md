# API reference

`dvv-workflow` exposes three usage tiers, each documented separately.

## High-level — one function call

```python
from dvv_workflow import run_workflow, load_site
```

→ [High-level API](high_level.md)

## Mid-level — phase by phase

```python
from dvv_workflow import Site, Phase0, Phase1, Phase2, Phase3, Phase4, Phase5, Phase6
```

→ [High-level API](high_level.md) (the Phase classes are documented there
  alongside `WorkflowResult`).

## Low-level — individual physics modules

```python
from dvv_workflow.forward.poroelastic import roeloffs_pressure_response
from dvv_workflow.forward.thermoelastic import berger_temperature_response
from dvv_workflow.forward.damage import snieder_healing
from dvv_workflow.coupling.tier1_poroelastic import drainage_peclet, frequency_dependent_beta_eff
from dvv_workflow.kernels.velocity_models import VelocityProfile, make_fine_model
from dvv_workflow.inverse.linear_fit import build_predictor_matrix, linear_fit
```

→ [Forward models](forward.md)
→ [Coupling diagnostics](coupling.md)
→ [Inversion](inverse.md)

## Stable vs experimental

| Module | Stability |
|---|---|
| `dvv_workflow.config` | stable |
| `dvv_workflow.workflow` | stable |
| `dvv_workflow.forward.{thermoelastic,poroelastic,damage}` | stable |
| `dvv_workflow.forward.{capillary,loading}` | experimental — physics in flux |
| `dvv_workflow.coupling.tier1_poroelastic` | stable |
| `dvv_workflow.coupling.{tier2,tier3,tier4}_*` | stub — v0.3+ |
| `dvv_workflow.inverse.linear_fit` | stable |
| `dvv_workflow.inverse.coupled_inversion` | stub — v0.2 |
| `dvv_workflow.interpretation.stress_at_depth` | stable |
| `dvv_workflow.interpretation.water_table` | stub — v0.2 |
| `dvv_workflow.kernels.disba_wrapper` | stable, optional |
| `dvv_workflow.kernels.depth_resolution` | stable |
| `dvv_workflow.data.loaders` | stable |
| `dvv_workflow.anomaly.detection` | stable |
| `dvv_workflow.anomaly.attribution` | experimental |

The "stable" modules will preserve their public signatures across
0.x releases unless flagged in the changelog.
