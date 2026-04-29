r"""
Prior helpers for the v0.2 MCMC backend.

For v0.1 (WLS), priors are not used in the inversion itself — they are still
recorded in the :class:`~codameter.config.MaterialProperties` of the Site
so the interpretation module can fold them into uncertainty propagation. The
helpers in this module compute log-prior contributions and validate the
prior dict that downstream MCMC code will consume.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np

from ..config import MaterialProperties, Prior


def gaussian_log_prior(value: float, prior: Prior) -> float:
    r"""Gaussian log-prior :math:`-\tfrac{1}{2}((x - \mu)/\sigma)^2`.

    Constants dropped (irrelevant for MCMC).
    """
    return -0.5 * ((value - prior.mean) / prior.std) ** 2


def validate_priors(material_properties: MaterialProperties) -> None:
    """Sanity-check that the priors are physically plausible.

    Raises ``ValueError`` if any prior allows obviously unphysical regions
    (e.g. negative porosity, beta with the wrong sign).
    """
    mp = material_properties
    if mp.porosity_prior.mean - 3 * mp.porosity_prior.std < 0:
        raise ValueError(
            f"Porosity prior mean={mp.porosity_prior.mean} std="
            f"{mp.porosity_prior.std} puts >3sigma below 0 (unphysical)"
        )
    if mp.porosity_prior.mean + 3 * mp.porosity_prior.std > 0.6:
        raise ValueError(
            f"Porosity prior mean={mp.porosity_prior.mean} std="
            f"{mp.porosity_prior.std} puts >3sigma above 0.6 (unphysical "
            f"for consolidated rock)"
        )
    if mp.skempton_B_prior.mean - 3 * mp.skempton_B_prior.std < 0 or (
        mp.skempton_B_prior.mean + 3 * mp.skempton_B_prior.std > 1.05
    ):
        raise ValueError(
            "Skempton's B prior should be tight on [0, 1]; got "
            f"mean={mp.skempton_B_prior.mean} std={mp.skempton_B_prior.std}"
        )
    if mp.biot_alpha_prior.mean - 3 * mp.biot_alpha_prior.std < 0 or (
        mp.biot_alpha_prior.mean + 3 * mp.biot_alpha_prior.std > 1.05
    ):
        raise ValueError(
            "Biot's alpha prior should be tight on [0, 1]; got "
            f"mean={mp.biot_alpha_prior.mean} std={mp.biot_alpha_prior.std}"
        )


def sample_priors(
    material_properties: MaterialProperties,
    n_samples: int = 1000,
    *,
    rng: np.random.Generator | None = None,
) -> dict[str, np.ndarray]:
    """Draw independent Gaussian samples from each material-property prior.

    Used by the interpretation module to propagate prior uncertainty into
    derived quantities (e.g. depth-resolved stress) when the linear fit only
    constrains amplitudes.
    """
    rng = np.random.default_rng() if rng is None else rng
    out: dict[str, np.ndarray] = {}
    for name, prior in material_properties.__dict__.items():
        if isinstance(prior, Prior):
            out[name] = rng.normal(prior.mean, prior.std, size=n_samples)
    return out


def stack_priors(priors: Iterable[Prior]) -> tuple[np.ndarray, np.ndarray]:
    """Stack a sequence of priors into ``(means, stds)`` arrays."""
    means = np.array([p.mean for p in priors], dtype=float)
    stds = np.array([p.std for p in priors], dtype=float)
    return means, stds
