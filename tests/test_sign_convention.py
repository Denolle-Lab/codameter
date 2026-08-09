"""The dv/v sign convention, locked for every estimator.

Convention (v0.4.0, physical dv/v): a velocity *increase* is positive.
``impose_dvv(ref, t, +x)`` compresses the coda toward zero lag (arrivals
earlier), and every estimator in ``METHODS`` must report ``+x`` back.
``dv/v = -epsilon / (1 + epsilon)`` where epsilon is the stretch factor (exact map).

History: before v0.4.0 the generator and the stretching-family estimators
(stretching TS, WCC, WTS) used the epsilon convention (positive = coda
dilation = slowdown) while DTW/MWCS/WCS/WTDTW were physical — internally
consistent goldens, but cross-estimator ensembles mixed signs, and cloud
dv/v anticorrelated with CD2022 and with seasonal hydrology at three CI
stations until the pipeline negated. Found on the noisepy-dvv-cloud
Gate 1 run, 2026-08-08.
"""

import numpy as np
import pytest
from codameter.deviations import METHODS, measure, run_pipeline
from codameter.synthetic_demo import impose_dvv, make_coda

TRUE_DVV = 0.003


@pytest.fixture(scope="module")
def scene():
    # the well-conditioned regime every estimator handles (the same one the
    # recover-small-dvv golden test uses): 50 sps, 0.5-2 Hz, 8-35 s coda
    t, ref = make_coda(seed=0)
    return t, ref


@pytest.mark.parametrize("name", list(METHODS))
@pytest.mark.parametrize("dv", [TRUE_DVV, -0.004])
def test_every_estimator_reports_physical_dvv(scene, name, dv):
    t, ref = scene
    cur = impose_dvv(ref, t, dv)[None, :]
    val = measure(name, cur, ref, t, band=(0.5, 2.0), fs=50.0, window=(8, 35))
    v = float(np.atleast_1d(val)[0])
    assert np.sign(v) == np.sign(
        dv
    ), f"{name}: imposed {dv:+}, reported {v:+.5f} — wrong sign"
    assert v == pytest.approx(dv, abs=1e-3)


def test_run_pipeline_reports_physical_dvv():
    t, ref = make_coda(seed=0)
    rng = np.random.default_rng(1)
    ndays = 200
    ccfs = np.empty((ndays, t.size))
    for d in range(ndays):
        dv = TRUE_DVV if d > 120 else 0.0
        ccfs[d] = impose_dvv(ref, t, dv) + 0.02 * rng.standard_normal(t.size)
    cfg = {
        "estimator": "stretching (TS)",
        "band": (0.5, 2.0),
        "window": (8.0, 35.0),
        "stack": 5,
        "reference": "fixed",
        "gate": None,
    }
    dvv, valid, cc = run_pipeline(ccfs, t, 50.0, cfg, eps_max=0.05, return_cc=True)
    tail = np.nanmedian(dvv[150:])
    assert tail == pytest.approx(TRUE_DVV, rel=0.2)
