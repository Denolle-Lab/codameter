r"""
Coupled inversion (Eq. 19 of Denolle, in prep) — **deferred to v0.2**.

When Phase 2 issues a hard escalation, the linear superposition (Eq. 6) is
known to be inadequate and the workflow should solve the full state-dependent
forward operator

.. math::
    \frac{d (\delta v / v)}{d t} = \mathcal{F}\!\left[
        T(t),\, p(t),\, S(t),\, \theta(t),\, ;\,
        \beta_{\rm eff}(\omega),\, \mu',\, \kappa,\, \tau_{\rm damage}, \ldots
    \right]

where the parameters are themselves state-dependent (see Eq. 19 and §10 of the
manuscript). The intended v0.2 implementation will:

1. Use the WLS amplitudes from :func:`linear_fit` as a starting point.
2. Sample :math:`\beta_{\rm eff}(\omega)`, :math:`\mu'`, hydraulic
   diffusivity, and the Snieder relaxation times jointly with `emcee`.
3. Use the prior dict from :class:`~dvv_workflow.config.MaterialProperties`
   for regularisation.

In v0.1 this is a stub that raises :class:`NotImplementedError`. The CLI
will surface this as a clear error message and recommend turning off the
hard-escalation check or waiting for v0.2.
"""
from __future__ import annotations

from typing import Any

import numpy as np


def coupled_inversion(
    *args: Any,
    **kwargs: Any,
) -> None:
    """Placeholder for the v0.2 coupled (nonlinear) inversion.

    Raises
    ------
    NotImplementedError
        Always — coupled inversion is scheduled for v0.2.
    """
    raise NotImplementedError(
        "coupled_inversion (Eq. 19) is deferred to v0.2 of dvv-workflow.\n"
        "For v0.1, use linear_fit() with the Phase-2 coupling diagnostics "
        "informing whether a hard escalation is warranted. If so, the "
        "recommended workaround is to:\n"
        "  - Restrict the linear fit to a band of the time series where "
        "    coupling is weakest (e.g. dry season), or\n"
        "  - Use the frequency-dependent beta_eff(omega) from Phase 2 as a "
        "    scalar correction in the Phase 6 interpretation."
    )


def state_dependent_forward(
    state: np.ndarray,
    *args: Any,
    **kwargs: Any,
) -> np.ndarray:
    """Placeholder for Eq. 19 (state-dependent forward operator).

    Will be implemented in v0.2 alongside :func:`coupled_inversion`.
    """
    raise NotImplementedError(
        "state_dependent_forward (Eq. 19) is deferred to v0.2 of dvv-workflow."
    )
