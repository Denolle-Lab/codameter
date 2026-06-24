"""Phase 0 data ingestion: loaders, QC, and covariate alignment."""

from __future__ import annotations

from .covariates import align_forcings, resample_to
from .loaders import (
    load_clements_denolle_2023,
    load_csv_timeseries,
    load_dvv,
    load_earthquake_catalog,
    load_timeseries,
)
from .property_providers import (
    DefaultPropertyProvider,
    PropertyResolution,
    UCVMProvider,
    USGSVs30Provider,
    default_velocity_model,
    resolve_site_properties,
)
from .qc import detect_gaps, flag_outliers, summarize_quality
from .readiness import DataReadinessReport, GoalReadiness, assess_data_readiness

__all__ = [
    "load_dvv",
    "load_csv_timeseries",
    "load_timeseries",
    "load_earthquake_catalog",
    "load_clements_denolle_2023",
    "assess_data_readiness",
    "DataReadinessReport",
    "GoalReadiness",
    "flag_outliers",
    "detect_gaps",
    "summarize_quality",
    "align_forcings",
    "resample_to",
    "PropertyResolution",
    "UCVMProvider",
    "USGSVs30Provider",
    "DefaultPropertyProvider",
    "default_velocity_model",
    "resolve_site_properties",
]
