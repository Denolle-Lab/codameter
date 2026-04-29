"""
dvv_workflow — operational pipeline for interpreting seismic velocity changes.

This package implements the six-phase workflow of Denolle (in prep, JGR Solid
Earth) for converting :math:`\\delta v / v` time series and environmental
forcings into stress, strain, water-table, and damage-state estimates with
propagated uncertainties.

The public API exposes three usage tiers:

1. **High-level** — :func:`run_workflow` and :class:`WorkflowResult`.
2. **Mid-level**  — :class:`Site` plus the six phase classes
   :class:`Phase0`, :class:`Phase1`, ..., :class:`Phase6`.
3. **Low-level**  — individual physics modules in
   :mod:`dvv_workflow.forward`, :mod:`dvv_workflow.coupling`, etc.

See ``docs/quickstart.md`` for a 5-minute walkthrough.
"""
from __future__ import annotations

from ._version import __version__
from .config import Site, load_site
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
    # Phase objects
    "Phase0",
    "Phase1",
    "Phase2",
    "Phase3",
    "Phase4",
    "Phase5",
    "Phase6",
]
