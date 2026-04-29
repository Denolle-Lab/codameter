r"""
Tier 4 — thermo-capillary coupling through the soil-water retention curve.
**Stub for v0.4.**

Following §9.5 of Denolle (in prep), Tier 4 captures the dependence of
suction stress on temperature through the SWRC (Vahedifard et al., 2020).
The diagnostic is the Pearson correlation :math:`\rho(T, S_w)` on seasonal
timescales: when :math:`|\rho| \gtrsim 0.5`, linear decomposition aliases
the SWRC shift into either the thermoelastic or hydrological coefficient.

Reference: Vahedifard, F., et al. (2018, 2020); Shi et al. (2026).
"""
from __future__ import annotations


def thermo_capillary_diagnostic(*args, **kwargs):
    """Stub. Raises :class:`NotImplementedError`."""
    raise NotImplementedError(
        "Tier 4 thermo-capillary diagnostic is scheduled for codameter v0.4."
    )
