"""Tests for the data-loaders module — including the Clements & Denolle 2023
compatibility layer.

These tests build small synthetic files that mimic the upstream archive
formats, so they pass without any external data download.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.feather as feather
import pytest

from codameter.data.loaders import (
    load_clements_denolle_2023,
    load_csv_timeseries,
    load_dvv,
    load_earthquake_catalog,
)


# ---------------------------------------------------------------------------
# Generic loaders
# ---------------------------------------------------------------------------


class TestLoadDvv:
    def test_csv_with_explicit_columns(self, tmp_path):
        # Build a tiny CSV
        idx = pd.date_range("2020-01-01", periods=5, freq="D")
        df = pd.DataFrame({
            "time": idx,
            "dvv": [0.001, 0.002, -0.001, 0.0, 0.0005],
            "dvv_err": [0.0001] * 5,
        })
        path = tmp_path / "dvv.csv"
        df.to_csv(path, index=False)
        loaded = load_dvv(path)
        assert len(loaded) == 5
        assert "dvv" in loaded.columns
        assert loaded["dvv"].iloc[0] == pytest.approx(0.001)
        assert loaded.index.tz is not None

    def test_parquet(self, tmp_path):
        idx = pd.date_range("2020-01-01", periods=5, freq="D", tz="UTC")
        df = pd.DataFrame({"dvv": np.arange(5) * 1e-3, "dvv_err": [1e-4] * 5},
                          index=idx)
        df.index.name = "time"
        path = tmp_path / "dvv.parquet"
        df.reset_index().to_parquet(path)
        loaded = load_dvv(path)
        assert len(loaded) == 5

    def test_percent_units_converted(self, tmp_path):
        idx = pd.date_range("2020-01-01", periods=3, freq="D")
        df = pd.DataFrame({"time": idx, "dvv": [0.1, 0.2, 0.3],
                           "dvv_err": [0.01, 0.01, 0.01]})
        path = tmp_path / "dvv.csv"
        df.to_csv(path, index=False)
        loaded = load_dvv(path, units="percent")
        assert loaded["dvv"].iloc[0] == pytest.approx(0.001)  # 0.1 % -> 0.001

    def test_warns_on_missing_err(self, tmp_path):
        idx = pd.date_range("2020-01-01", periods=3, freq="D")
        df = pd.DataFrame({"time": idx, "dvv": [0.001, 0.002, 0.003]})
        path = tmp_path / "dvv.csv"
        df.to_csv(path, index=False)
        with pytest.warns(UserWarning, match="dvv_err column not found"):
            loaded = load_dvv(path)
        assert (loaded["dvv_err"] == 1e-3).all()


class TestLoadCsvTimeseries:
    def test_load_precipitation(self, tmp_path):
        idx = pd.date_range("2020-01-01", periods=10, freq="D")
        df = pd.DataFrame({"time": idx, "precipitation": np.arange(10) * 0.001})
        path = tmp_path / "P.csv"
        df.to_csv(path, index=False)
        loaded = load_csv_timeseries(path)
        assert len(loaded) == 10
        assert loaded.name == "precipitation"
        assert loaded.iloc[5] == pytest.approx(0.005)

    def test_ambiguous_value_column_raises(self, tmp_path):
        idx = pd.date_range("2020-01-01", periods=10, freq="D")
        df = pd.DataFrame({
            "time": idx,
            "precip": np.arange(10) * 0.001,
            "temp": np.arange(10) * 0.5,
        })
        path = tmp_path / "multi.csv"
        df.to_csv(path, index=False)
        with pytest.raises(ValueError, match="ambiguous"):
            load_csv_timeseries(path)


class TestLoadEarthquakeCatalog:
    def test_radius_filter(self, tmp_path):
        idx = pd.date_range("2020-01-01", periods=4, freq="D")
        df = pd.DataFrame({
            "time": idx,
            "latitude": [35.97, 36.0, 40.0, 45.0],
            "longitude": [-120.55, -120.5, -120.0, -118.0],
            "depth_km": [10.0] * 4,
            "magnitude": [3.0, 4.5, 5.0, 6.0],
        })
        path = tmp_path / "eq.csv"
        df.to_csv(path, index=False)
        loaded = load_earthquake_catalog(
            path, site_lat=35.97, site_lon=-120.55,
            search_radius_km=50.0, min_magnitude=4.0,
        )
        assert len(loaded) == 1  # only the M4.5 nearby

    def test_distance_column_added(self, tmp_path):
        idx = pd.date_range("2020-01-01", periods=2, freq="D")
        df = pd.DataFrame({
            "time": idx,
            "latitude": [35.97, 36.0],
            "longitude": [-120.55, -120.5],
            "magnitude": [4.0, 5.0],
        })
        path = tmp_path / "eq.csv"
        df.to_csv(path, index=False)
        loaded = load_earthquake_catalog(path, site_lat=35.97, site_lon=-120.55)
        assert "distance_km" in loaded.columns


# ---------------------------------------------------------------------------
# Clements & Denolle (2023) compatibility
# ---------------------------------------------------------------------------


def _build_fake_cd_archive(root: Path, station: str = "CI.LJR") -> Path:
    """
    Build a tiny mock archive that mimics the on-disk layout of the
    Clements & Denolle (2023) Zenodo data:
      {root}/DVV/{station}.feather
    Columns: DATE (timestamp), DVV (percent), CC (correlation).
    """
    dvv_dir = root / "DVV"
    dvv_dir.mkdir(parents=True, exist_ok=True)
    n = 800
    idx = pd.date_range("2002-01-01", periods=n, freq="D", tz="UTC")
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "DATE": idx.tz_convert(None),     # feather strips tz; the loader re-localises
        "DVV": (rng.standard_normal(n) * 0.05).cumsum(),  # in percent
        "CC": rng.uniform(0.6, 0.95, n),
    })
    table = pa.Table.from_pandas(df, preserve_index=False)
    feather.write_feather(table, dvv_dir / f"{station}.feather")
    return dvv_dir / f"{station}.feather"


class TestLoadClementsDenolle2023:
    def test_loads_feather(self, tmp_path):
        _build_fake_cd_archive(tmp_path)
        df = load_clements_denolle_2023(tmp_path, station="CI.LJR")
        # Has the required columns and is in fraction (not percent)
        assert "dvv" in df.columns
        assert "dvv_err" in df.columns
        assert df["dvv"].abs().max() < 0.1  # was percent (~5 %), now fraction (~0.0005)

    def test_metadata(self, tmp_path):
        _build_fake_cd_archive(tmp_path)
        df, meta = load_clements_denolle_2023(
            tmp_path, station="CI.LJR", return_metadata=True
        )
        assert meta["station"] == "CI.LJR"
        assert meta["n_samples"] == len(df)
        assert "source_file" in meta

    def test_missing_station_raises(self, tmp_path):
        _build_fake_cd_archive(tmp_path)
        with pytest.raises(FileNotFoundError, match="No dv/v file"):
            load_clements_denolle_2023(tmp_path, station="UU.NOPE")

    def test_post_conversion_parquet_layout(self, tmp_path):
        # Some users convert the upstream feather to flat parquet; the loader
        # should pick those up too.
        n = 200
        idx = pd.date_range("2002-01-01", periods=n, freq="D", tz="UTC")
        df = pd.DataFrame({
            "DATE": idx.tz_convert(None),
            "DVV": np.linspace(-0.5, 0.5, n),  # in percent
            "CC": np.full(n, 0.8),
        })
        df.to_parquet(tmp_path / "CI.NJQ.parquet")
        loaded = load_clements_denolle_2023(tmp_path, station="CI.NJQ")
        assert len(loaded) == n
        # 0.5 % -> 0.005 fraction
        assert loaded["dvv"].max() == pytest.approx(0.005, abs=1e-6)
