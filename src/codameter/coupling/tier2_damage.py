r"""
Tier 2 — damage--permeability coupling diagnostics. **Stub for v0.2.**

The intended diagnostic, following §9.3 of Denolle (in prep):

1. Identify earthquakes during the monitoring period with PGV > ~0.2 cm/s
   at the site.
2. Compute the seasonal :math:`\delta v / v` amplitude (peak-to-trough annual
   range) in sliding 2-year windows.
3. A step change in seasonal amplitude after the earthquake, followed by
   gradual recovery, diagnoses Tier 2 coupling.
4. Alternative: track tidal :math:`\beta` in sliding windows. A
   post-earthquake decrease (more drained at tidal frequencies due to
   enhanced permeability), followed by recovery, gives the same diagnostic
   independently of meteorological variability.

References
----------
- Elkhoury, J. E., Brodsky, E. E., & Agnew, D. C. (2006). Seismic waves
  increase permeability. *Nature*, 441, 1135--1138.
- Xue, L., et al. (2013). Continuous permeability measurements record
  healing inside the Wenchuan earthquake fault zone. *Science*, 340,
  1555--1559.
- Illien, L., Sens-Schoenfelder, C., Andermann, C., Marc, O., Hovius, N.
  (2022). Subsurface moisture regulates Himalayan groundwater storage and
  discharge. *AGU Advances*, 3, e2022AV000651.
"""
from __future__ import annotations


def damage_permeability_split_window(*args, **kwargs):
    """Stub. Raises :class:`NotImplementedError`."""
    raise NotImplementedError(
        "Tier 2 damage-permeability diagnostic is scheduled for "
        "codameter v0.3. See §9.3 of Denolle (in prep) for the "
        "framework, and contact the authors for the prototype "
        "implementation in coupling_tier_tests.py."
    )
