"""
Forcing-time-series alignment.

The dv/v series and each environmental forcing typically arrive on different
sampling grids (precipitation daily, temperature hourly, dv/v sub-daily to
weekly depending on smoothing). The functions here put them all on a single
common grid for downstream regression, in a way that respects the physical
units of each channel.
"""
from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

# Default aggregation rules. Anything not listed defaults to mean.
_DEFAULT_AGG = {
    "precipitation": "sum",
    "precip": "sum",
    "rain": "sum",
    "snowmelt": "sum",
    "swe": "mean",
    "temperature": "mean",
    "T": "mean",
    "groundwater_level": "mean",
    "gwl": "mean",
    "soil_moisture": "mean",
    "tide_strain": "mean",
}


def resample_to(
    series: pd.Series | pd.DataFrame,
    target_index: pd.DatetimeIndex,
    *,
    method: str = "linear",
    aggregation: str | None = None,
) -> pd.Series | pd.DataFrame:
    """Resample a time series onto ``target_index``.

    Parameters
    ----------
    series
        Input series or frame (UTC ``DatetimeIndex``).
    target_index
        The target ``DatetimeIndex`` to resample onto.
    method
        ``"linear"`` (default), ``"nearest"``, ``"ffill"``, or
        ``"aggregate"``. The ``aggregate`` mode bins the source into the
        intervals defined by ``target_index`` using ``aggregation`` (mean by
        default). This is appropriate when the source has *higher* sampling
        than the target — e.g. daily rain into 90-day dv/v bins.
    aggregation
        For ``method="aggregate"``: ``"sum"``, ``"mean"``, ``"max"``, ``"min"``.
    """
    if not isinstance(series.index, pd.DatetimeIndex):
        raise TypeError("series must have a DatetimeIndex")

    if method == "aggregate":
        agg = aggregation or "mean"
        # Resample to the target spacing, anchored at the target start
        spacing = target_index.to_series().diff().median()
        if pd.isna(spacing):
            raise ValueError("target_index too short to infer spacing")
        rule = f"{int(spacing.total_seconds())}s"
        resampled = series.resample(rule, origin=target_index[0]).agg(agg)
        return resampled.reindex(target_index)

    if method == "linear":
        return _interp_to(series, target_index, kind="linear")
    if method == "nearest":
        return _interp_to(series, target_index, kind="nearest")
    if method == "ffill":
        return series.reindex(series.index.union(target_index)).sort_index().ffill().reindex(target_index)
    raise ValueError(f"Unknown resampling method {method!r}")


def align_forcings(
    dvv: pd.DataFrame,
    forcings: Mapping[str, pd.Series],
    *,
    method: str = "auto",
) -> pd.DataFrame:
    """Resample every forcing onto the dv/v index and return as one frame.

    Parameters
    ----------
    dvv
        The dv/v frame whose index defines the target grid.
    forcings
        Mapping ``{name: series}`` of environmental forcings.
    method
        Either an explicit method (see :func:`resample_to`) or ``"auto"``
        (the default) which picks a sensible aggregation for each known
        channel name.

    Returns
    -------
    pandas.DataFrame
        Indexed by ``dvv.index``, with one column per forcing.
    """
    target = dvv.index
    cols: dict[str, pd.Series] = {}
    for name, s in forcings.items():
        if method == "auto":
            agg = _DEFAULT_AGG.get(name.lower(), "mean")
            if agg in {"sum", "max", "min"}:
                cols[name] = resample_to(
                    s, target, method="aggregate", aggregation=agg
                )
            else:
                cols[name] = resample_to(s, target, method="linear")
        else:
            cols[name] = resample_to(s, target, method=method)
    return pd.DataFrame(cols, index=target)


def _interp_to(
    series: pd.Series | pd.DataFrame,
    target_index: pd.DatetimeIndex,
    *,
    kind: str,
) -> pd.Series | pd.DataFrame:
    """Time-aware interpolation onto a target index."""
    combined = series.reindex(series.index.union(target_index)).sort_index()
    if kind == "linear":
        combined = combined.interpolate(method="time")
    elif kind == "nearest":
        combined = combined.interpolate(method="nearest")
    else:
        raise ValueError(kind)
    return combined.reindex(target_index)
