"""
Forward forcing models (Phase 3).

Each module implements one physical pathway from an environmental forcing
to a predicted :math:`\\delta v / v` time series. The models are intentionally
kept small and side-effect-free so they can be combined linearly in
:mod:`codameter.inverse.linear_fit` and nonlinearly in
:mod:`codameter.inverse.coupled_inversion`.

References
----------
- :mod:`thermoelastic` — Berger (1975), Ben-Zion & Leary (1986),
  Richter et al. (2014).
- :mod:`poroelastic`  — Roeloffs (1988), Talwani et al. (2007),
  Clements & Denolle (2023, Eqs. 8--9), Fokker et al. (2021).
- :mod:`capillary`    — Shi et al. (2026), Vahedifard et al. (2018, 2020).
- :mod:`loading`      — Tsai (2011) surface-load Green's functions.
- :mod:`damage`       — Snieder et al. (2017) logarithmic healing.
"""
from __future__ import annotations

from .damage import logarithmic_healing, snieder_healing
from .loading import surface_load_dvv
from .poroelastic import (
    drained_pressure_response,
    groundwater_level_okubo,
    roeloffs_pressure_response,
    talwani_precipitation_response,
)
from .thermoelastic import (
    berger_temperature_response,
    fourier_temperature_decomposition,
    thermal_skin_depth,
    thermoelastic_dvv,
)

__all__ = [
    "thermoelastic_dvv",
    "berger_temperature_response",
    "fourier_temperature_decomposition",
    "thermal_skin_depth",
    "roeloffs_pressure_response",
    "talwani_precipitation_response",
    "drained_pressure_response",
    "groundwater_level_okubo",
    "surface_load_dvv",
    "logarithmic_healing",
    "snieder_healing",
]
