"""CLI smoke tests for user-facing data ingestion paths."""

from __future__ import annotations

import numpy as np
import pandas as pd

from codameter.cli import main
from codameter.data.readiness import assess_data_readiness


def test_run_cli_loads_series_forcings(tmp_path, synthetic_data):
    site_path = tmp_path / "site.yaml"
    synthetic_data["site"].to_yaml(site_path)

    dvv_path = tmp_path / "dvv.parquet"
    synthetic_data["dvv"].reset_index(names="time").to_parquet(dvv_path)

    precip_path = tmp_path / "precip.csv"
    temp_path = tmp_path / "temp.csv"
    forcing_index = synthetic_data["forcings"]["precipitation"].index
    pd.DataFrame(
        {
            "time": forcing_index,
            "precipitation": synthetic_data["forcings"]["precipitation"].values,
        }
    ).to_csv(precip_path, index=False)
    pd.DataFrame(
        {
            "time": forcing_index,
            "temperature": synthetic_data["forcings"]["temperature"].values,
        }
    ).to_csv(temp_path, index=False)

    out = tmp_path / "run"
    code = main(
        [
            "run",
            "--config",
            str(site_path),
            "--dvv",
            str(dvv_path),
            "--precip",
            str(precip_path),
            "--temp",
            str(temp_path),
            "--output",
            str(out),
            "--no-plot",
        ]
    )

    assert code == 0
    assert (out / "summary.txt").exists()
    assert (out / "results.json").exists()


def test_data_check_reports_missing_goal_inputs(tmp_path, capsys):
    idx = pd.date_range("2020-01-01", periods=10, freq="D", tz="UTC")
    dvv = pd.DataFrame({"time": idx, "dvv": np.linspace(0.0, 1e-3, len(idx))})
    dvv_path = tmp_path / "dvv.csv"
    dvv.to_csv(dvv_path, index=False)

    code = main(["data-check", "--dvv", str(dvv_path), "--goal", "groundwater"])
    captured = capsys.readouterr()

    assert code == 0
    assert "groundwater or soil-moisture monitoring" in captured.out
    assert "measurement uncertainty column 'dvv_err'" in captured.out
    assert "one hydrologic driver or proxy" in captured.out


def test_data_check_can_fail_on_missing(tmp_path):
    idx = pd.date_range("2020-01-01", periods=5, freq="D", tz="UTC")
    dvv = pd.DataFrame({"time": idx, "dvv": np.zeros(len(idx))})
    dvv_path = tmp_path / "dvv.csv"
    dvv.to_csv(dvv_path, index=False)

    code = main(
        [
            "data-check",
            "--dvv",
            str(dvv_path),
            "--goal",
            "stress",
            "--fail-on-missing",
        ]
    )

    assert code == 1


def test_assess_data_readiness_with_site_and_forcings(synthetic_data):
    report = assess_data_readiness(
        synthetic_data["dvv"],
        site=synthetic_data["site"],
        forcings=synthetic_data["forcings"],
        earthquake_catalog=synthetic_data["earthquake_times"],
        goals=["coupling"],
    )

    assert not report.has_missing_required
    goal = report.goals[0]
    assert goal.goal == "coupling"
    assert goal.status == "ready_for_exploratory_fit"
