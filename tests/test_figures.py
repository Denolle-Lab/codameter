"""Tests for the figure driver and its numerical sidecars (audit REP-01)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib
import numpy as np
import pytest

matplotlib.use("Agg")

from codameter import figures as F  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def test_sidecar_round_trips_every_plotted_array(tmp_path):
    import matplotlib.pyplot as plt

    fig, (a, b) = plt.subplots(1, 2)
    x = np.linspace(0, 1, 7)
    a.plot(x, x**2, label="quad")
    a.fill_between(x, 0, x, label="band")
    a.scatter(x, 1 - x)
    a.set(title="left", xlabel="t", ylabel="v")
    b.imshow(np.arange(6.0).reshape(2, 3), extent=[0, 3, 0, 2])
    b.bar([0, 1], [2.0, 3.0])
    png = F.save_figure(
        fig,
        tmp_path,
        "unit",
        generator="test",
        extra_arrays={"truth": x},
        extra_meta={"note": {"n": np.int64(7)}},
    )
    assert png.exists()
    z = np.load(tmp_path / "unit.npz")
    np.testing.assert_allclose(z["ax0/line0/y"], x**2)
    assert "ax0/collection0/vertices" in z  # fill_between polygon
    assert "ax0/collection1/offsets" in z  # scatter
    np.testing.assert_allclose(z["ax1/image0"], np.arange(6.0).reshape(2, 3))
    assert z["ax1/patch0/xywh"][3] == pytest.approx(2.0)
    np.testing.assert_allclose(z["data/truth"], x)
    assert z["data/truth"].dtype == np.float64  # small arrays are exact
    big = np.random.default_rng(0).standard_normal(F.LARGE_ARRAY + 1)
    F.save_figure(fig, tmp_path, "big", generator="test", extra_arrays={"big": big})
    zb = np.load(tmp_path / "big.npz")
    assert zb["data/big"].dtype == np.float32
    np.testing.assert_allclose(zb["data/big"], big, rtol=1e-6)
    meta = json.loads((tmp_path / "unit.json").read_text())
    assert meta["generator"] == "test" and meta["note"] == {"n": 7}
    assert meta["axes"][0]["lines"] == ["quad"] and meta["axes"][0]["title"] == "left"
    assert set(meta["arrays"]) == set(z.files)
    plt.close(fig)


def test_every_manuscript_figure_has_a_generator_or_a_declared_source():
    qmd = ROOT / "paper" / "manuscript_marine.qmd"
    if not qmd.exists():
        pytest.skip("manuscript not present")
    included = re.findall(
        r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", qmd.read_text()
    )
    stems = {Path(p).stem for p in included}
    known = set(F.generators()) | set(F.EXTERNAL)
    assert stems <= known, sorted(stems - known)
    assert F.SLOW <= set(F.generators())


def test_cli_lists_and_rejects_unknown(tmp_path, capsys):
    assert F.main(["--list"]) == 0
    out = capsys.readouterr().out
    assert "demo_12_bayes" in out and "realdata_1_validation" in out
    with pytest.raises(KeyError):
        F.build_all_figures(tmp_path, only=["no_such_figure"])


def test_sidecar_records_dirty_flag_and_generator_digest(tmp_path):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    F.save_figure(fig, tmp_path, "prov", generator="test")
    plt.close(fig)
    meta = json.loads((tmp_path / "prov.json").read_text())
    assert meta["generator_digest"] == F.generator_digest()
    assert re.fullmatch(r"[0-9a-f]{12}", meta["generator_digest"])
    assert meta["git_dirty"] in (True, False, None)
    assert meta["git_commit"] is None or re.fullmatch(
        r"[0-9a-f]{40}", meta["git_commit"]
    )


def test_compare_sidecar_reports_differences(tmp_path):
    big = np.linspace(0, 1, F.LARGE_ARRAY + 1)
    arrays = {"ax0/line0/y": np.array([1.0, 2.0, np.nan]), "data/big": big}
    np.savez_compressed(
        tmp_path / "s.npz", **{k: F.compact_array(v) for k, v in arrays.items()}
    )
    assert F.compare_sidecar(arrays, tmp_path / "s.npz") == []
    # float32 storage of the large array is not a difference
    assert (
        F.compare_sidecar(
            dict(arrays, **{"data/big": big * (1 + 1e-8)}), tmp_path / "s.npz"
        )
        == []
    )
    # rounding noise on an entry that is zero up to arithmetic is not a difference
    tiny = {"ax0/line0/y": np.array([1e-18, 0.5]), "data/big": big}
    np.savez_compressed(tmp_path / "t.npz", **tiny)
    shifted = dict(tiny, **{"ax0/line0/y": np.array([-3e-18, 0.5])})
    assert F.compare_sidecar(shifted, tmp_path / "t.npz") == []
    moved = dict(tiny, **{"ax0/line0/y": np.array([1e-18, 0.5001])})
    assert F.compare_sidecar(moved, tmp_path / "t.npz") != []
    # the scale comes from either array: a stored zero against a large value differs
    zeros = {"ax0/line0/y": np.zeros(2), "data/big": big}
    np.savez_compressed(tmp_path / "z.npz", **zeros)
    assert (
        F.compare_sidecar(
            dict(zeros, **{"ax0/line0/y": np.array([0.0, 0.5])}), tmp_path / "z.npz"
        )
        != []
    )
    assert (
        F.compare_sidecar(
            dict(zeros, **{"ax0/line0/y": np.array([0.0, 1e-18])}), tmp_path / "z.npz"
        )
        != []
    )
    # arrays differing only in NaN placement: one message, no warning
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        d = F.compare_sidecar(
            dict(zeros, **{"ax0/line0/y": np.array([0.0, np.nan])}), tmp_path / "z.npz"
        )
    assert d == ["ax0/line0/y: values differ only in NaN placement"]
    diffs = F.compare_sidecar(
        {"ax0/line0/y": np.array([1.0, 2.5, np.nan]), "data/other": big},
        tmp_path / "s.npz",
    )
    assert any("values differ" in d for d in diffs)
    assert any("no longer generated" in d for d in diffs)
    assert any("new array" in d for d in diffs)
    assert F.compare_sidecar(arrays, tmp_path / "missing.npz") == [
        f"no committed sidecar at {tmp_path / 'missing.npz'}"
    ]


def test_missing_inputs_are_skipped_not_fatal(tmp_path, monkeypatch, capsys):
    from codameter.errors import MissingInputs

    def _gen():
        raise MissingInputs("no data here")

    monkeypatch.setattr(F, "generators", lambda: {"needs_data": ("test", _gen)})
    assert F.build_all_figures(tmp_path, only=["needs_data"]) == []
    assert "skipped: no data here" in capsys.readouterr().out
    assert F.check_all_figures(tmp_path, only=["needs_data"]) == {}


def test_gate1_generator_is_registered_and_needs_data():
    assert "realdata_1_validation" in F.generators()
    assert "realdata_1_validation" not in F.EXTERNAL
    assert "realdata_1_validation" in F.NEEDS_DATA


def test_gate1_generator_skips_when_inputs_are_absent(tmp_path):
    from codameter.errors import MissingInputs
    from codameter.gate1 import fig_gate1_comparison

    with pytest.raises(MissingInputs):
        fig_gate1_comparison(gate1=tmp_path)  # no comparison.json, no products
