r"""
Tier 3 — saturation-dependent nonlinear elasticity. **Stub for v0.3.**

Intended diagnostic, following §9.4 of Denolle (in prep):

1. Compute a 90-day antecedent precipitation index (API).
2. Compute :math:`d(\delta v/v)/d(\rm precip)` in sliding windows.
3. A non-constant sensitivity — largest during drought-to-wet transitions
   when saturation crosses the capillary sensitivity window — confirms
   state-dependent :math:`\beta(S_w)`.
4. Independent corroboration with soil-moisture probes when available.

Reference: Shi et al. (2026); Van Den Abeele et al. (2002); Winkler &
McGowan (2004).
"""
from __future__ import annotations


def saturation_sensitivity_diagnostic(*args, **kwargs):
    """Stub. Raises :class:`NotImplementedError`."""
    raise NotImplementedError(
        "Tier 3 saturation-dependent diagnostic is scheduled for "
        "codameter v0.3."
    )
