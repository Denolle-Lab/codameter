"""
Data loaders for dv/v time series, environmental forcings, and earthquake
catalogs.

All loaders return either a :class:`pandas.DataFrame` indexed by
``DatetimeIndex`` (UTC) or, for the dv/v data specifically, a frame with the
required columns ``["dvv", "dvv_err"]``. Optional columns such as
``"correlation_coefficient"`` are preserved.
"""

from __future__ import annotations

import warnings
from collections.abc import Iterable
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Generic loaders
# ---------------------------------------------------------------------------


def load_dvv(
    path: str | Path,
    *,
    time_column: str | None = None,
    dvv_column: str = "dvv",
    err_column: str | None = "dvv_err",
    correlation_column: str | None = "cc",
    units: str = "fraction",
) -> pd.DataFrame:
    """Load a dv/v time series from CSV or parquet.

    Parameters
    ----------
    path
        Path to the file. Format is inferred from the extension
        (``.csv`` / ``.tsv`` / ``.parquet`` / ``.feather``).
    time_column
        Name of the time column. If ``None``, the loader looks for
        ``"time"``, ``"date"``, ``"datetime"``, ``"t"`` (case-insensitive),
        or uses the index if it is already datetime-typed.
    dvv_column
        Column with the dv/v measurement (default ``"dvv"``).
    err_column
        Column with the standard error of the dv/v measurement. If absent,
        a default of ``0.1 %`` is filled in and a warning is emitted.
    correlation_column
        Column with the coda-cross-correlation coefficient, used for QC
        weighting. Optional.
    units
        Either ``"fraction"`` (e.g. 0.001 = 0.1 %) or ``"percent"``. The
        returned frame is always in fraction.

    Returns
    -------
    pandas.DataFrame
        Indexed by UTC ``DatetimeIndex``, with columns
        ``["dvv", "dvv_err"]`` and any optional columns preserved.
    """
    path = Path(path)
    df = _read_table(path)
    df = _index_by_time(df, time_column)
    df = df.sort_index()

    # Column normalisation
    if dvv_column not in df.columns:
        raise KeyError(
            f"dvv column {dvv_column!r} not found in {path}; "
            f"available: {list(df.columns)}"
        )
    out = pd.DataFrame(index=df.index)
    out["dvv"] = df[dvv_column].astype(float)

    err_defaulted = False
    if err_column and err_column in df.columns:
        out["dvv_err"] = df[err_column].astype(float)
    else:
        warnings.warn(
            f"dvv_err column not found in {path.name}; "
            "defaulting to dvv_err = 0.001 (0.1 %). Provide an err column for "
            "proper WLS weighting in Phase 3.",
            UserWarning,
            stacklevel=2,
        )
        out["dvv_err"] = 1e-3
        err_defaulted = True

    if correlation_column and correlation_column in df.columns:
        out["cc"] = df[correlation_column].astype(float)

    if units == "percent":
        out["dvv"] = out["dvv"] / 100.0
        out["dvv_err"] = out["dvv_err"] / 100.0
    elif units != "fraction":
        raise ValueError(f"units must be 'fraction' or 'percent', got {units!r}")

    out.attrs["dvv_err_defaulted"] = err_defaulted
    out.attrs["dvv_units"] = "fraction"
    return out


def load_csv_timeseries(
    path: str | Path,
    *,
    time_column: str | None = None,
    value_column: str | None = None,
) -> pd.Series:
    """Load a single-column scalar time series (precipitation, temperature, ...).

    Returns
    -------
    pandas.Series
        Indexed by UTC ``DatetimeIndex`` with the original column name.
    """
    df = _read_table(Path(path))
    df = _index_by_time(df, time_column)
    df = df.sort_index()
    if value_column is None:
        non_time = [c for c in df.columns if c.lower() not in _TIME_NAMES]
        if len(non_time) != 1:
            raise ValueError(
                f"value_column not given and ambiguous: candidates {non_time}"
            )
        value_column = non_time[0]
    return df[value_column].astype(float).rename(value_column)


def load_timeseries(
    path: str | Path,
    *,
    time_column: str | None = None,
    value_column: str | None = None,
) -> pd.Series:
    """Load a scalar time series from CSV, TSV, Parquet, Feather, or Arrow.

    This is a clearer alias for :func:`load_csv_timeseries`, which predates
    Parquet/Feather support and is kept for backward compatibility.
    """
    return load_csv_timeseries(
        path,
        time_column=time_column,
        value_column=value_column,
    )


def load_earthquake_catalog(
    path: str | Path,
    *,
    site_lat: float | None = None,
    site_lon: float | None = None,
    search_radius_km: float | None = None,
    min_magnitude: float | None = None,
) -> pd.DataFrame:
    """Load an earthquake catalog and optionally filter to a site neighbourhood.

    The catalog must have ``time``, ``latitude``, ``longitude``, ``depth_km``,
    and ``magnitude`` columns (case-insensitive). Output columns are
    standardised to ``["latitude", "longitude", "depth_km", "magnitude",
    "distance_km"]`` indexed by event time.
    """
    df = _read_table(Path(path))
    df.columns = [c.strip().lower() for c in df.columns]
    df = _index_by_time(df, time_column="time")
    df = df.sort_index()

    rename = {
        "lat": "latitude",
        "lon": "longitude",
        "depth": "depth_km",
        "mag": "magnitude",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    required = {"latitude", "longitude", "magnitude"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"earthquake catalog missing required columns: {missing}")
    if "depth_km" not in df.columns:
        df["depth_km"] = np.nan

    # Optional spatial filter
    if site_lat is not None and site_lon is not None:
        df["distance_km"] = _haversine_km(
            site_lat, site_lon, df["latitude"].to_numpy(), df["longitude"].to_numpy()
        )
        if search_radius_km is not None:
            df = df[df["distance_km"] <= search_radius_km]
    if min_magnitude is not None:
        df = df[df["magnitude"] >= min_magnitude]

    return df[
        ["latitude", "longitude", "depth_km", "magnitude"]
        + (["distance_km"] if "distance_km" in df.columns else [])
    ]


# ---------------------------------------------------------------------------
# Clements & Denolle (2023) loader
# ---------------------------------------------------------------------------


def load_clements_denolle_2023(
    data_dir: str | Path,
    station: str,
    *,
    component: str = "EN-EZ-NZ",
    frequency_band_hz: tuple[float, float] = (2.0, 4.0),
    return_metadata: bool = False,
) -> pd.DataFrame | tuple[pd.DataFrame, dict]:
    """
    Load a station's dv/v from the Clements & Denolle (2023) Zenodo archive.

    The archive (DOI 10.5281/zenodo.6413275, ``data-0.2.0.zip``, 4.4 GB) is the
    output of the Julia pipeline in
    https://github.com/Denolle-Lab/Clements-Denolle-2022. After unpacking, the
    relevant files are stored as Apache Arrow / Feather format under
    ``DVV/`` (one file per network.station). Companion meteorological data is
    provided as PRISM netCDF files, which can be loaded separately via
    :func:`load_csv_timeseries` after extraction.

    This loader is tolerant of three layouts the upstream archive has used:

    1. ``{data_dir}/DVV/{station}.feather``
    2. ``{data_dir}/DVV/{station}.arrow``
    3. ``{data_dir}/{station}.parquet`` (post-conversion to parquet)

    Parameters
    ----------
    data_dir
        Path to the unpacked Zenodo archive root.
    station
        Network and station code, e.g. ``"CI.LJR"``.
    component
        Component combination — pass-through for documentation; the upstream
        pipeline writes the combined EN-EZ-NZ stack as the default.
    frequency_band_hz
        Frequency band metadata for the loaded series (used downstream by
        Phase 1 to anchor the sensitivity kernels). The 2--4 Hz default
        matches the band used in the original paper.
    return_metadata
        If ``True``, also return a dict with the file path, station code,
        frequency band, and any extracted columns.

    Returns
    -------
    pandas.DataFrame
        Indexed by UTC ``DatetimeIndex``, with at least
        ``["dvv", "dvv_err"]``. The dv/v is in fraction (the upstream Julia
        pipeline writes percent; this loader converts).
    """
    data_dir = Path(data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(
            f"Clements & Denolle data directory not found: {data_dir}"
        )

    candidates = [
        data_dir / "DVV" / f"{station}.feather",
        data_dir / "DVV" / f"{station}.arrow",
        data_dir / f"{station}.feather",
        data_dir / f"{station}.arrow",
        data_dir / f"{station}.parquet",
    ]
    file = next((c for c in candidates if c.exists()), None)
    if file is None:
        raise FileNotFoundError(
            f"No dv/v file for station {station!r} under {data_dir}. "
            f"Looked for: {[str(c) for c in candidates]}.\n"
            f"If you have the raw Julia .arrow output, you can also drop a "
            f"converted .parquet file directly into {data_dir}."
        )

    df = _read_table(file)
    df.columns = [c.strip().lower() for c in df.columns]

    # Map upstream column names to our schema. The Julia pipeline historically
    # writes columns named "DATE", "DVV", and either "CC" or "Q".
    if "date" in df.columns:
        df = df.set_index(pd.to_datetime(df["date"], utc=True)).drop(columns="date")
    else:
        df = _index_by_time(df, time_column=None)

    if "dvv" not in df.columns:
        raise KeyError(
            f"Loaded file {file} has no 'dvv' column; columns are {list(df.columns)}"
        )

    out = pd.DataFrame(index=df.index)
    # Upstream stores percent — convert to fraction
    out["dvv"] = df["dvv"].astype(float) / 100.0
    err_defaulted = False
    if "dvv_err" in df.columns:
        out["dvv_err"] = df["dvv_err"].astype(float) / 100.0
    elif "err" in df.columns:
        out["dvv_err"] = df["err"].astype(float) / 100.0
    else:
        # Empirical floor used by the original paper for unweighted sites
        out["dvv_err"] = 1e-3
        err_defaulted = True
    if "cc" in df.columns:
        out["cc"] = df["cc"].astype(float)
    elif "q" in df.columns:
        out["cc"] = df["q"].astype(float)

    out = out.sort_index()
    out = out[~out.index.duplicated(keep="first")]
    out.attrs["dvv_err_defaulted"] = err_defaulted
    out.attrs["dvv_units"] = "fraction"

    if return_metadata:
        meta = {
            "source_file": str(file),
            "station": station,
            "component": component,
            "frequency_band_hz": tuple(frequency_band_hz),
            "n_samples": len(out),
            "time_range": (out.index.min(), out.index.max()),
        }
        return out, meta
    return out


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


_TIME_NAMES = {"time", "date", "datetime", "t", "timestamp"}


def _read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".tsv":
        return pd.read_csv(path, sep="\t")
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if suffix in {".feather", ".arrow"}:
        return pd.read_feather(path)
    raise ValueError(
        f"Unsupported file format: {suffix!r}. "
        "Supported: .csv, .tsv, .parquet, .feather, .arrow"
    )


def _index_by_time(df: pd.DataFrame, time_column: str | None) -> pd.DataFrame:
    if time_column is None:
        # Already datetime-indexed?
        if isinstance(df.index, pd.DatetimeIndex):
            return df.tz_localize("UTC") if df.index.tz is None else df
        # Auto-detect
        for c in df.columns:
            if c.lower() in _TIME_NAMES:
                time_column = c
                break
        if time_column is None:
            raise KeyError(
                f"No time column found; columns: {list(df.columns)}. "
                "Pass time_column= explicitly."
            )
    times = pd.to_datetime(df[time_column], utc=True, errors="coerce")
    if times.isna().any():
        n_bad = int(times.isna().sum())
        warnings.warn(
            f"{n_bad} rows had unparseable times in column {time_column!r}; "
            "they were dropped.",
            UserWarning,
            stacklevel=2,
        )
        df = df.loc[times.notna()].copy()
        times = times.dropna()
    df = df.set_index(times).drop(columns=[time_column])
    df.index.name = "time"
    return df


def _haversine_km(
    lat1: float,
    lon1: float,
    lat2: float | Iterable[float],
    lon2: float | Iterable[float],
) -> np.ndarray:
    R = 6371.0
    lat1r = np.deg2rad(lat1)
    lon1r = np.deg2rad(lon1)
    lat2r = np.deg2rad(lat2)
    lon2r = np.deg2rad(lon2)
    dlat = lat2r - lat1r
    dlon = lon2r - lon1r
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1r) * np.cos(lat2r) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
