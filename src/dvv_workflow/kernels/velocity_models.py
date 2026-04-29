"""
Velocity-profile utilities.

The :func:`make_fine_model` function discretises a coarse layered model
(typically 3--5 layers) onto a fine grid suitable for sensitivity-kernel
computation. It is a direct port of the helper used in the manuscript's
``notebooks/06b_sensitivity_kernel_disba.ipynb`` and is the canonical place
to add layers — every other module in :mod:`dvv_workflow.kernels` consumes
its output.

Convention
----------
All depths and thicknesses are in **kilometres**.
All velocities are in **km/s**.
All densities are in **g/cm^3**.

These match the disba (Luu, 2021) input convention and avoid any unit
gymnastics inside the workflow.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class VelocityProfile:
    """A discretised layered Earth model.

    Attributes
    ----------
    thickness : np.ndarray, shape (N,)
        Layer thicknesses in km. The last entry can be 0 to denote a
        half-space (disba convention).
    vp : np.ndarray, shape (N,)
        P-wave velocity in km/s.
    vs : np.ndarray, shape (N,)
        S-wave velocity in km/s.
    rho : np.ndarray, shape (N,)
        Density in g/cm^3.
    """

    thickness: np.ndarray
    vp: np.ndarray
    vs: np.ndarray
    rho: np.ndarray

    def __post_init__(self) -> None:
        arrs = (self.thickness, self.vp, self.vs, self.rho)
        n = len(self.thickness)
        for arr, name in zip(arrs, ("thickness", "vp", "vs", "rho")):
            if len(arr) != n:
                raise ValueError(
                    f"VelocityProfile arrays must all have the same length; "
                    f"{name} has length {len(arr)}, expected {n}"
                )
        if np.any(self.vs <= 0):
            raise ValueError("vs must be strictly positive")
        if np.any(self.vp <= self.vs * np.sqrt(2)):
            raise ValueError(
                "vp/vs ratio implies negative Poisson's ratio in at least one layer"
            )

    @property
    def n_layers(self) -> int:
        return len(self.thickness)

    @property
    def depths(self) -> np.ndarray:
        """Depth to the *top* of each layer in km."""
        return np.concatenate([[0.0], np.cumsum(self.thickness)[:-1]])

    @property
    def midpoint_depths(self) -> np.ndarray:
        """Depth to the centre of each layer in km."""
        return self.depths + self.thickness / 2.0

    def shear_modulus_GPa(self) -> np.ndarray:
        r""":math:`\\mu = \\rho V_S^2`. Result in GPa."""
        # rho in g/cm^3 = 10^3 kg/m^3; vs in km/s = 10^3 m/s
        # mu = 10^3 * (10^3)^2 = 10^9 Pa = GPa
        return self.rho * self.vs**2

    def bulk_modulus_GPa(self) -> np.ndarray:
        r""":math:`\\kappa = \\rho (V_P^2 - 4 V_S^2 / 3)`. Result in GPa."""
        return self.rho * (self.vp**2 - 4.0 * self.vs**2 / 3.0)

    def to_arrays(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Return (thickness, vp, vs, rho) tuple in disba's preferred order."""
        return self.thickness, self.vp, self.vs, self.rho


def make_fine_model(
    coarse_thickness_km: np.ndarray | list[float],
    coarse_vp: np.ndarray | list[float],
    coarse_vs: np.ndarray | list[float],
    coarse_rho: np.ndarray | list[float],
    *,
    target_dz_km: float = 0.01,
    max_depth_km: float | None = None,
) -> VelocityProfile:
    """Discretise a coarse layered model onto a fine grid.

    The disba sensitivity-kernel computation needs a finely-discretised
    model to produce smooth depth profiles. This helper takes a coarse
    description (typically 3--5 layers from a published velocity model) and
    interpolates each layer onto a uniform-thickness grid of step
    ``target_dz_km``.

    The half-space layer (the last layer in the input, conventionally given
    a large thickness) is included in the output but with a single thick
    entry rather than fine-grid replication, to keep the matrix size
    manageable.

    Parameters
    ----------
    coarse_thickness_km, coarse_vp, coarse_vs, coarse_rho
        The coarse model. ``coarse_thickness_km`` should be in km;
        velocities in km/s; density in g/cm^3.
    target_dz_km
        Target grid spacing in km. Default 0.01 km (10 m), suitable for
        ambient-noise frequencies of 0.1--10 Hz.
    max_depth_km
        If given, truncate the model at this depth (and replace the deepest
        finite layer below it with a half-space using its properties).

    Returns
    -------
    VelocityProfile
    """
    thick = np.asarray(coarse_thickness_km, dtype=float)
    vp = np.asarray(coarse_vp, dtype=float)
    vs = np.asarray(coarse_vs, dtype=float)
    rho = np.asarray(coarse_rho, dtype=float)

    if not (len(thick) == len(vp) == len(vs) == len(rho)):
        raise ValueError("coarse arrays must all have the same length")
    if target_dz_km <= 0:
        raise ValueError("target_dz_km must be positive")

    fine_thick: list[float] = []
    fine_vp: list[float] = []
    fine_vs: list[float] = []
    fine_rho: list[float] = []

    depth_so_far = 0.0
    for i in range(len(thick) - 1):  # Skip the half-space (last layer)
        layer_top = depth_so_far
        layer_bot = depth_so_far + thick[i]
        if max_depth_km is not None and layer_top >= max_depth_km:
            break
        if max_depth_km is not None and layer_bot > max_depth_km:
            layer_bot = max_depth_km

        n_sub = max(1, int(np.ceil((layer_bot - layer_top) / target_dz_km)))
        sub_dz = (layer_bot - layer_top) / n_sub
        for _ in range(n_sub):
            fine_thick.append(sub_dz)
            fine_vp.append(vp[i])
            fine_vs.append(vs[i])
            fine_rho.append(rho[i])
        depth_so_far = layer_bot

    # Append the half-space with the original (or last truncated) properties
    fine_thick.append(thick[-1])  # disba treats nonzero last as half-space too
    fine_vp.append(vp[-1])
    fine_vs.append(vs[-1])
    fine_rho.append(rho[-1])

    return VelocityProfile(
        thickness=np.array(fine_thick),
        vp=np.array(fine_vp),
        vs=np.array(fine_vs),
        rho=np.array(fine_rho),
    )
