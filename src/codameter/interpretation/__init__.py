r"""
Phase 6 — interpretation.

Convert the inverted amplitudes (Phase 4) and the depth-resolution table
(Phase 1) into the *physical* observables of interest:

* Pore pressure / equivalent water-table change at the kernel depth.
* Mean and deviatoric stress at the kernel depth via the bridge relation
  :math:`\beta = -\mu' \kappa / (2 \mu)` (Eq. 7 of Denolle, in prep).
* Damage state (per-event coseismic drop).

In v0.1 the water-table inversion is a simple scalar conversion; the full
state-dependent water-table reconstruction is deferred to v0.2.
"""
from __future__ import annotations

from .stress_at_depth import (
    StressEstimate,
    bridge_relation,
    beta_to_stress_sensitivity,
    stress_at_depth_from_pressure,
)
from .water_table import (
    WaterTableEstimate,
    pressure_to_head_change,
)

__all__ = [
    "bridge_relation",
    "beta_to_stress_sensitivity",
    "stress_at_depth_from_pressure",
    "StressEstimate",
    "pressure_to_head_change",
    "WaterTableEstimate",
]
