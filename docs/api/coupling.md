# Coupling diagnostics

## Tier 1 — poroelastic (operational in v0.1)

::: dvv_workflow.coupling.tier1_poroelastic
    options:
      show_root_heading: false
      members:
        - drainage_peclet
        - frequency_dependent_beta_eff
        - tidal_beta_estimate

## Decision tree

::: dvv_workflow.coupling.decision_tree
    options:
      show_root_heading: false
      members:
        - CouplingReport
        - escalation_decision
        - diagnose_all_tiers

## Tiers 2, 3, 4 — stubs

Tier 2 (damage–permeability), Tier 3 (saturation-dependent
nonlinear elasticity), and Tier 4 (thermo-capillary) modules exist
as planning placeholders. Their public API will land in v0.3 / v0.4.
