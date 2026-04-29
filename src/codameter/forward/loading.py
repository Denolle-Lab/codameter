r"""
Surface-load forward model.

A point or distributed load on the surface produces an instantaneous elastic
deformation that compresses the subsurface and *increases* :math:`\delta v / v`,
opposing the pore-pressure effect (Fokker et al., 2021). For an axisymmetric
surface load on a uniform half-space, the vertical strain at depth :math:`z`
is given by the Boussinesq solution (Love, 1929; Tsai, 2011).

For practical use with hydrological loading, we provide a simplified model
that treats the load as the column of water above the site and converts to
vertical stress :math:`\sigma_{zz} = \rho g h`, with the standard load-Love-
number type response. This is appropriate for spatially extended loading
(e.g. snowpack, reservoir impoundment) but conservative for compact loading.

References
----------
- Boussinesq, J. (1885). *Application des potentiels...*
- Tsai, V. C. (2011). A model for seasonal changes in GPS positions and
  seismic wave speeds due to thermoelastic and hydrologic variations.
  *J. Geophys. Res.*, 116, B04404.
- Fokker, E., Ruigrok, E., Hawkins, R., & Trampert, J. (2021).
  Physics-based relationship for pore pressure and vertical stress
  monitoring using seismic velocity variations. *Remote Sensing*, 13, 2684.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def surface_load_dvv(
    load_height_m: np.ndarray | pd.Series,
    *,
    beta: float,
    rho_load: float = 1000.0,
    g: float = 9.81,
    mu_GPa: float = 1.0,
    bulk_modulus_GPa: float = 5.0,
) -> np.ndarray:
    r"""Surface-loading :math:`\delta v / v` from a column-equivalent load.

    For a uniform vertical stress :math:`\sigma_{zz} = \rho g h`, the
    induced volumetric strain in a uniform elastic medium is
    :math:`\varepsilon_v = \sigma_{zz} / (3\kappa)`. The corresponding
    velocity change uses the acoustoelastic coefficient :math:`\beta`:

    .. math::
        \frac{\delta v}{v}(t) = \beta \cdot \varepsilon_v(t)
                              = \beta \cdot \rho g h(t) / (3 \kappa).

    Parameters
    ----------
    load_height_m
        Equivalent water column or load height in metres.
    beta
        Dimensionless acoustoelastic coefficient (negative for most rocks;
        Cascadia ~ -3160; Parkfield ~ -240). See Fokker et al. (2021)
        Eq. 7 and the bridge relation in Denolle (in prep).
    rho_load
        Density of the load material (kg/m^3). Default 1000 (water).
    g
        Gravity (m/s^2).
    mu_GPa, bulk_modulus_GPa
        Shear and bulk moduli of the rock at the kernel depth, in GPa.
        Defaults are crude crustal averages and should be supplied from
        Phase 1 in production use.

    Returns
    -------
    np.ndarray
        :math:`\delta v / v` (fraction).
    """
    h = np.asarray(load_height_m, dtype=float)
    sigma_zz = rho_load * g * h  # Pa
    bulk_Pa = bulk_modulus_GPa * 1e9
    eps_v = sigma_zz / (3.0 * bulk_Pa)
    return beta * eps_v
