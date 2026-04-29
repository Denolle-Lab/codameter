"""End-to-end synthetic Parkfield test of the full six-phase workflow.

This is the integration test that catches wiring problems between the phases.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from codameter import run_workflow


class TestEndToEnd:
    def test_pipeline_runs(self, synthetic_data):
        s = synthetic_data
        result = run_workflow(
            s["dvv"], s["forcings"], s["site"],
            earthquake_times=s["earthquake_times"],
        )
        # Result has all six phases populated
        for phase_name in ["phase0", "phase1", "phase2", "phase3", "phase4",
                           "phase5", "phase6"]:
            assert getattr(result, phase_name) is not None

    def test_reduced_chi_square_near_one(self, synthetic_data):
        s = synthetic_data
        result = run_workflow(
            s["dvv"], s["forcings"], s["site"],
            earthquake_times=s["earthquake_times"],
        )
        assert 0.7 < result.phase4.fit.chi2_reduced < 1.4

    def test_truth_recovery(self, synthetic_data):
        """Recovers the synthetic p1, p2 amplitudes within 4σ."""
        s = synthetic_data
        result = run_workflow(
            s["dvv"], s["forcings"], s["site"],
            earthquake_times=s["earthquake_times"],
        )
        truth = s["truth"]
        for name, true_val in [
            ("p1_dGWL", truth["p1_dGWL"]),
            ("p2_T", truth["p2_T"]),
        ]:
            mean, std = result.phase4.fit.posterior.marginal(name)
            assert abs((mean - true_val) / std) < 4, (
                f"{name}: truth {true_val:+.3e} vs fit {mean:+.3e} ± {std:.2e}"
            )

    def test_residuals_pass_whiteness(self, synthetic_data):
        s = synthetic_data
        result = run_workflow(
            s["dvv"], s["forcings"], s["site"],
            earthquake_times=s["earthquake_times"],
        )
        # By construction the synthetic noise is white -> p > 0.05
        assert result.phase5.report.whiteness_pvalue > 0.05

    def test_phase6_pressure_sensitivity_nonzero(self, synthetic_data):
        s = synthetic_data
        result = run_workflow(
            s["dvv"], s["forcings"], s["site"],
            earthquake_times=s["earthquake_times"],
        )
        ps = result.phase6.pressure_sensitivity
        assert ps is not None
        mean, std = ps
        # Sign convention: positive pressure -> negative dv/v
        assert mean < 0
        # Recovered uncertainty should be small
        assert std < abs(mean)

    def test_summary_string_runs(self, synthetic_data):
        s = synthetic_data
        result = run_workflow(
            s["dvv"], s["forcings"], s["site"],
            earthquake_times=s["earthquake_times"],
        )
        summary = result.summary()
        assert "phase 0" in summary.lower() or "Phase 0" in summary
        assert "Phase 6" in summary

    def test_export_writes_files(self, synthetic_data):
        s = synthetic_data
        result = run_workflow(
            s["dvv"], s["forcings"], s["site"],
            earthquake_times=s["earthquake_times"],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir)
            result.export(out)
            assert (out / "summary.txt").exists()
            assert (out / "results.json").exists()
            assert (out / "parameters.csv").exists()
            assert (out / "residuals.csv").exists()
            results = json.loads((out / "results.json").read_text())
            assert results["site_id"] == s["site"].site_id

    def test_to_dict_serialisable(self, synthetic_data):
        s = synthetic_data
        result = run_workflow(
            s["dvv"], s["forcings"], s["site"],
            earthquake_times=s["earthquake_times"],
        )
        # Round-trip through json to verify serialisability
        json.dumps(result.to_dict(), default=str)
