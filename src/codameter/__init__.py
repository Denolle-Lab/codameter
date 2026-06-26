"""
codameter — operational pipeline for interpreting seismic velocity changes.

This package implements the six-phase workflow of Denolle (in prep, JGR Solid
Earth) for converting :math:`\\delta v / v` time series and environmental
forcings into stress, strain, water-table, and damage-state estimates with
propagated uncertainties.

The public API exposes three usage tiers:

1. **High-level** — :func:`run_workflow` and :class:`WorkflowResult`.
2. **Mid-level**  — :class:`Site` plus the six phase classes
   :class:`Phase0`, :class:`Phase1`, ..., :class:`Phase6`.
3. **Low-level**  — individual physics modules in
   :mod:`codameter.forward`, :mod:`codameter.coupling`, etc.

See ``docs/quickstart.md`` for a 5-minute walkthrough.
"""

from __future__ import annotations

from ._version import __version__
from .config import Site, load_site
from .data.readiness import DataReadinessReport, GoalReadiness, assess_data_readiness
from .uq_depth import (
    DepthKernels,
    DepthProfilePosterior,
    band_sensitivity_matrix,
    invert_depth_profile,
)
from .uq_measurement import (
    EnsembleResult,
    GlobalReferenceSolution,
    effective_sample_size,
    global_reference_inversion,
    processing_ensemble,
    single_reference_dvv,
    temporal_error_covariance,
    weaver_stretching_error,
)
from .uq_processing import (
    ProcessingChoice,
    ProcessingPrior,
    per_band_marginal_error,
    sample_processing_choices,
)
from .workflow import (
    Phase0,
    Phase1,
    Phase2,
    Phase3,
    Phase4,
    Phase5,
    Phase6,
    WorkflowResult,
    run_workflow,
)

__all__ = [
    "__version__",
    # High-level
    "run_workflow",
    "WorkflowResult",
    # Configuration
    "Site",
    "load_site",
    # Data guidance
    "assess_data_readiness",
    "DataReadinessReport",
    "GoalReadiness",
    # Measurement (aleatoric) uncertainty of the dv/v observation
    "weaver_stretching_error",
    "processing_ensemble",
    "EnsembleResult",
    "temporal_error_covariance",
    "effective_sample_size",
    "global_reference_inversion",
    "GlobalReferenceSolution",
    "single_reference_dvv",
    # Processing-choice (nuisance) uncertainty
    "ProcessingPrior",
    "ProcessingChoice",
    "sample_processing_choices",
    "per_band_marginal_error",
    # Frequency -> depth propagation
    "band_sensitivity_matrix",
    "DepthKernels",
    "invert_depth_profile",
    "DepthProfilePosterior",
    # Phase objects
    "Phase0",
    "Phase1",
    "Phase2",
    "Phase3",
    "Phase4",
    "Phase5",
    "Phase6",
]
