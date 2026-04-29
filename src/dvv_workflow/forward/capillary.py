r"""
Capillary / unsaturated-zone forward model.

In partially saturated granular media, the shear-wave velocity depends on
the effective shear modulus :math:`\mu_{\rm eff}` through Hertz-Mindlin
contact stiffness with a saturation-dependent effective pressure that
includes capillary suction (Shi et al., 2026; Vahedifard et al., 2018).
This produces hysteretic :math:`\delta v / v` signatures during wetting--drying
cycles that are not captured by the saturated poroelastic models in
:mod:`dvv_workflow.forward.poroelastic`.

This module is **scheduled for v0.2** with the Tier 3 coupling extension.
For now it provides a stub that explains the equations and raises
:class:`NotImplementedError`. The relevant physics is documented inline so
that the placeholder is informative.

References
----------
- Shi, Y., et al. (2026). Dynamic capillary effects in partially saturated
  soils observed with distributed acoustic sensing. *Science*.
- Vahedifard, F., et al. (2018, 2020). Soil water retention curve under
  thermal cycling. (See manuscript reference list.)
"""
from __future__ import annotations

import numpy as np


def capillary_dvv(
    saturation: np.ndarray | float,
    *,
    pressure_effective_Pa: float | np.ndarray = 1.0e5,
    suction_Pa: float | np.ndarray = 0.0,
    contact_exponent: float = 1.0 / 3.0,
) -> np.ndarray:
    r"""**Stub** — saturation-dependent :math:`\delta v / v`.

    The intended formulation, following Shi et al. (2026), is:

    .. math::
        \frac{\delta v}{v}(S_w) = \tfrac{1}{2}\,\frac{\delta \mu_{\rm eff}}{\mu_{\rm eff}}
            \quad\text{with}\quad
            \mu_{\rm eff} \propto P_{\rm e}^{1/3},
            \quad
            P_{\rm e} = P_{\rm overburden} + \sigma_s(S_w),

    where :math:`\sigma_s(S_w)` is the saturation-dependent suction stress.

    Raises
    ------
    NotImplementedError
        Always, until v0.2.
    """
    raise NotImplementedError(
        "Capillary / Tier-3 forward model is scheduled for dvv-workflow v0.2. "
        "For now, treat saturation effects as part of the residual in "
        "Phase 5, or supply an empirical S_w-dependent beta to the "
        "linear regression. See §9.4 of Denolle (in prep) for the full "
        "Tier 3 framework."
    )


def soil_water_retention_curve(
    suction_Pa: np.ndarray | float,
    *,
    alpha_per_Pa: float = 1e-4,
    n: float = 2.0,
    saturation_residual: float = 0.05,
    saturation_max: float = 1.0,
) -> np.ndarray:
    r"""van Genuchten (1980) soil-water retention curve.

    .. math::
        S_w(\psi) = S_r + (S_{\max} - S_r)
                    \left[1 + (\alpha |\psi|)^n\right]^{-(1 - 1/n)}.

    Provided as a utility for prospective Tier 3 / Tier 4 work — not used
    by the v0.1 inversion.
    """
    psi = np.atleast_1d(np.asarray(suction_Pa, dtype=float))
    psi = np.abs(psi)
    m = 1.0 - 1.0 / n
    Se = (1.0 + (alpha_per_Pa * psi) ** n) ** (-m)
    return saturation_residual + (saturation_max - saturation_residual) * Se
