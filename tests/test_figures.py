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
