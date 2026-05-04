"""Phase 2 coupling diagnostics.

The coupling tier hierarchy follows §9 of Denolle (in prep, JGR Solid
Earth):

- **Tier 1** poroelastic coupling — drainage Péclet number, frequency-
  dependent :math:`\\beta_{\\rm eff}` (Eq. 15)
- **Tier 2** damage--permeability feedback — split-window analysis around
  earthquakes (Eq. 16)
- **Tier 3** saturation-dependent nonlinear elasticity — antecedent-
  precipitation-index (API)-dependent sensitivity
- **Tier 4** thermo-capillary SWRC coupling

In v0.1, only Tier 1 is implemented. Tiers 2--4 expose stubs with
:class:`NotImplementedError` and detailed inline guidance for what the
next-version implementation must do.
"""
from __future__ import annotations

from .decision_tree import CouplingReport, diagnose_all_tiers, escalation_decision
from .tier1_poroelastic import (
    drainage_peclet,
    frequency_dependent_beta_eff,
    tidal_beta_estimate,
)
from .tier2_damage import damage_permeability_split_window
from .tier3_saturation import saturation_sensitivity_diagnostic
from .tier4_thermo_capillary import thermo_capillary_diagnostic

__all__ = [
    "CouplingReport",
    "diagnose_all_tiers",
    "escalation_decision",
    "drainage_peclet",
    "frequency_dependent_beta_eff",
    "tidal_beta_estimate",
    "damage_permeability_split_window",
    "saturation_sensitivity_diagnostic",
    "thermo_capillary_diagnostic",
]
