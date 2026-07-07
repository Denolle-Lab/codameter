r"""Golden synthetic datasets for dv/v processing: a seeded, reproducible corpus.

Two consumers share one source of truth:

- **CI** -- :mod:`tests.test_golden` regenerates each case from its seed and
  asserts that the recommended pipeline recovers the known dv/v within the
  frozen tolerance, so a regression in any estimator or in ``run_pipeline`` is
  caught.
- **The advisor** -- the ``codameter-advisor`` skill loads a matched case to
  quantify, live, the bias and error-bar cost of a user's processing choices.

Design: the committed artifact is ``tests/data/golden/manifest.json`` -- the
**recipes plus expected metrics**, not the arrays. A full multi-year daily CCF
stack is tens of MB and is fully determined by its seed, so the arrays are
regenerated on demand and cached under ``tests/data/golden/cache/`` (gitignored).

Two families of case:

- **mainstream** -- one per application in :data:`codameter.use_cases.USE_CASES`,
  synthesized with that application's matched geometry and typical SNR. The
  recommended config should recover the truth cleanly (low RMS).
- **edge** -- the four failure regimes the survey warns about: low SNR with a
  large (cycle-skipping) dv/v; clock drift plus seasonal late-coda noise; a
  frequency-dependent shallow+deep medium where the band selects the depth; and
  sparse cadence with waveform decorrelation. For these the oracle pins the
  *magnitude of the artifact* (RMS within a band around the frozen value), so
  the deterministic failure mode cannot silently change.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import use_cases as uc
from .deviations import run_pipeline
from .synthetic_demo import (
    YEAR_D, _days, _seasonal, add_clock_drift, add_seasonal_late_noise,
    daily_ccfs, earthquake_truth, groundwater_truth, landslide_truth,
    make_coda, volcano_truth,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "tests" / "data" / "golden"
MANIFEST = DATA_DIR / "manifest.json"
CACHE_DIR = DATA_DIR / "cache"
MANIFEST_VERSION = 1


# ---------------------------------------------------------------------------
# Ground-truth generators, resolved by name from use_cases[...]["dvv"].
# Volcano/earthquake/landslide/groundwater reuse synthetic_demo; cryosphere and
# geothermal get local builders (adjusted amplitude) until dedicated ones exist.
# ---------------------------------------------------------------------------
def _cryosphere_truth(days: np.ndarray) -> np.ndarray:
    """Sharp seasonal freeze-thaw swing (~ +/-3.5 %), summer velocity minimum."""
    return _seasonal(days, 0.035, 200.0)


def _geothermal_truth(days: np.ndarray) -> np.ndarray:
    """Slow injection-driven decline (~ -1 %) with a muted seasonal overlay."""
    ramp = -0.010 * np.clip((days - 0.3 * YEAR_D) / (2.0 * YEAR_D), 0, 1)
    return ramp + _seasonal(days, 0.0004, 30.0)


TRUTH = {
    "volcano": volcano_truth,
    "earthquake": earthquake_truth,
    "landslide": landslide_truth,
    "groundwater_shallow": lambda days: groundwater_truth(days)[0],
    "groundwater_deep": lambda days: groundwater_truth(days)[1],
    "cryosphere": _cryosphere_truth,
    "geothermal": _geothermal_truth,
}


# ---------------------------------------------------------------------------
# Case recipes. Each is a plain dict (no computed metrics); the manifest adds
# the expected metrics at regeneration time.
#
#   id          : unique case identifier / cache key.
#   kind        : "mainstream" | "edge".
#   use_case    : USE_CASES key; sets config, synth geometry, eps_max, truth.
#   years, snr, seed : synthesis controls.
#   decorr      : waveform-decorrelation fraction (daily_ccfs).
#   cadence     : keep every Nth day (sparse sampling); default 1.
#   artifacts   : list of injectors applied after daily_ccfs.
#   config      : optional per-axis overrides on the recommended config.
#   probes      : optional [{label, config-overrides, truth}] extra measurements
#                 whose RMS is also frozen (used to prove band-selects-depth).
#   rms_rel_tol : allowed fractional drift of RMS around the frozen value.
# ---------------------------------------------------------------------------
CASES: list[dict] = [
    # ---- mainstream: one per application -------------------------------
    {"id": "volcano_mainstream", "kind": "mainstream", "use_case": "volcano",
     "years": 3.0, "snr": 7.0, "seed": 11, "rms_rel_tol": 0.30},
    {"id": "earthquake_mainstream", "kind": "mainstream", "use_case": "earthquake_fault",
     "years": 3.0, "snr": 7.0, "seed": 12, "rms_rel_tol": 0.30},
    {"id": "landslide_mainstream", "kind": "mainstream", "use_case": "landslide",
     "years": 3.0, "snr": 8.0, "seed": 13, "rms_rel_tol": 0.30},
    {"id": "groundwater_mainstream", "kind": "mainstream", "use_case": "groundwater",
     "years": 3.0, "snr": 8.0, "seed": 14, "rms_rel_tol": 0.30},
    {"id": "cryosphere_mainstream", "kind": "mainstream", "use_case": "cryosphere",
     "years": 3.0, "snr": 8.0, "seed": 15, "rms_rel_tol": 0.30},
    {"id": "geothermal_mainstream", "kind": "mainstream", "use_case": "geothermal",
     "years": 3.0, "snr": 7.0, "seed": 16, "rms_rel_tol": 0.30},

    # ---- edge: low SNR + large (cycle-skipping) dv/v -------------------
    {"id": "low_snr_large_dvv", "kind": "edge", "use_case": "landslide",
     "years": 3.0, "snr": 2.0, "seed": 21, "rms_rel_tol": 0.35,
     "note": "SNR~2 with a several-percent pre-failure drop: the regime that "
             "splits stretching from cross-spectral methods."},

    # ---- edge: clock drift + seasonal late-coda noise ------------------
    {"id": "clock_drift_seasonal", "kind": "edge", "use_case": "volcano",
     "years": 3.0, "snr": 7.0, "seed": 22, "rms_rel_tol": 0.35,
     "artifacts": [
         {"kind": "clock_drift", "drift_s_per_day": 2.0e-4, "onset_day": 200},
         {"kind": "seasonal_late_noise", "onset_s": 20.0, "dvv_amp": 0.004,
          "jitter": 0.06},
     ],
     "note": "A growing clock error plus a seasonal late-coda warp inject a "
             "spurious dv/v (Zhan 2013 / Daskalakis 2016)."},

    # ---- edge: frequency-dependent shallow + deep medium ---------------
    {"id": "freqdep_shallow_deep", "kind": "edge", "use_case": "groundwater",
     "years": 3.0, "snr": 9.0, "seed": 23, "rms_rel_tol": 0.35,
     "two_layer": True,
     "config": {"band": (4.0, 10.0), "window": (2.0, 8.0)},
     "probes": [
         {"label": "deep_band_recovers_deep",
          "config": {"band": (0.2, 1.0), "window": (8.0, 25.0)},
          "truth": "deep"},
     ],
     "note": "Shallow (high-freq) and deep (low-freq) layers carry different "
             "dv/v; the band selects which one you recover."},

    # ---- edge: sparse cadence + waveform decorrelation -----------------
    {"id": "sparse_decorr", "kind": "edge", "use_case": "volcano",
     "years": 3.0, "snr": 6.0, "seed": 24, "cadence": 3, "decorr": 0.30,
     "rms_rel_tol": 0.35,
     "note": "Every-third-day sampling with 30 % waveform decorrelation stresses "
             "the reference/stacking warm-up."},
]

CASES_BY_ID = {c["id"]: c for c in CASES}

# Application -> its mainstream golden case, so the advisor can pull a matched
# synthetic for any use case without hardcoding ids.
MAINSTREAM_BY_USE_CASE = {
    c["use_case"]: c["id"] for c in CASES if c["kind"] == "mainstream"
}


def case_split(recipe: dict) -> str:
    """Benchmark split for a case: mainstream -> validation, edge -> test.

    (These are the frugalmind splits; a recipe may override with a ``split`` key.)
    """
    return recipe.get("split", "validation" if recipe["kind"] == "mainstream" else "test")


def case_visibility(recipe: dict) -> str:
    """Benchmark visibility. Synthetic and seed-reproducible, so public by default."""
    return recipe.get("visibility", "public")


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------
def _synth_reference(use_case: str):
    """One reference coda + its lapse axis, matched to the use case geometry."""
    sp = uc.synth_params(use_case)
    t, ref = make_coda(maxlag_s=sp["maxlag_s"], fs=sp["fs"],
                       band=sp["gen_band"], t_coda_s=sp["t_coda_s"], seed=0)
    return t, ref, sp


def _build(recipe: dict) -> dict:
    """Regenerate the arrays for one case deterministically from its recipe."""
    use_case = recipe["use_case"]
    sp = uc.synth_params(use_case)
    fs, gen_band = sp["fs"], sp["gen_band"]
    days = _days(recipe["years"])
    seed = recipe["seed"]
    snr = recipe["snr"]
    decorr = recipe.get("decorr", 0.0)

    out: dict = {"fs": fs, "days": days, "use_case": use_case}

    if recipe.get("two_layer"):
        # Two band-separated layers so the frequency band selects the depth.
        t, shallow = make_coda(maxlag_s=sp["maxlag_s"], fs=fs, band=(3.0, 11.0),
                               t_coda_s=sp["t_coda_s"], seed=0)
        _, deep = make_coda(maxlag_s=sp["maxlag_s"], fs=fs, band=(0.2, 1.1),
                            t_coda_s=sp["t_coda_s"], seed=1)
        truth_s = TRUTH["groundwater_shallow"](days)
        truth_d = TRUTH["groundwater_deep"](days)
        ccfs = daily_ccfs(t, [shallow, deep], [truth_s, truth_d], fs=fs,
                          snr=snr, decorr=decorr, gen_band=gen_band, seed=seed)
        out.update(t=t, ccfs=ccfs, truth=truth_s, truth_deep=truth_d)
    else:
        t, ref, _ = _synth_reference(use_case)
        truth = TRUTH[uc.USE_CASES[use_case]["dvv"]](days)
        ccfs = daily_ccfs(t, [ref], [truth], fs=fs, snr=snr, decorr=decorr,
                          gen_band=gen_band, seed=seed)
        out.update(t=t, ccfs=ccfs, truth=truth)

    for art in recipe.get("artifacts", []):
        ccfs = out["ccfs"]
        if art["kind"] == "clock_drift":
            ccfs = add_clock_drift(ccfs, out["t"],
                                   drift_s_per_day=art["drift_s_per_day"],
                                   onset_day=art.get("onset_day", 0))
        elif art["kind"] == "seasonal_late_noise":
            ccfs = add_seasonal_late_noise(
                ccfs, out["t"], out["days"], fs=fs, onset_s=art["onset_s"],
                dvv_amp=art.get("dvv_amp", 0.004), jitter=art.get("jitter", 0.06),
                band=gen_band, seed=seed + 100)
        else:
            raise ValueError(f"unknown artifact {art['kind']!r}")
        out["ccfs"] = ccfs

    # Sparse sampling last, so injectors see the full daily record.
    cadence = recipe.get("cadence", 1)
    if cadence > 1:
        idx = np.arange(0, len(out["days"]), cadence)
        out["days"] = out["days"][idx]
        out["ccfs"] = out["ccfs"][idx]
        out["truth"] = out["truth"][idx]
        if "truth_deep" in out:
            out["truth_deep"] = out["truth_deep"][idx]
    return out


def generate(case_id: str, *, cache: bool = True) -> dict:
    """Return ``{ccfs, t, days, truth[, truth_deep], fs, use_case}`` for a case.

    Deterministic in the recipe seed. When ``cache`` is set the arrays are read
    from / written to ``tests/data/golden/cache/<id>.npz`` to avoid recomputing.
    """
    recipe = CASES_BY_ID[case_id]
    cache_file = CACHE_DIR / f"{case_id}.npz"
    if cache and cache_file.exists():
        z = np.load(cache_file, allow_pickle=False)
        d = {k: z[k] for k in z.files}
        d["fs"] = float(d["fs"])
        d["use_case"] = str(d["use_case"])
        return d
    d = _build(recipe)
    if cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            cache_file,
            **{k: np.asarray(v) for k, v in d.items()
               if k in ("ccfs", "t", "days", "truth", "truth_deep")},
            fs=np.asarray(d["fs"]), use_case=np.asarray(d["use_case"]))
    return d


# ---------------------------------------------------------------------------
# Metrics oracle
# ---------------------------------------------------------------------------
def _rms(dvv, truth, days, valid, baseline_frac: float = 0.2) -> float:
    """Baseline-aligned RMS error of a recovered dv/v series against the truth.

    A dv/v estimate is relative to a reference epoch, so its absolute level (the
    DC offset) is not observable: a fixed reference measures change *since the
    baseline window*, not since zero. We therefore remove, from both the
    recovered and the true series, their mean over the earliest ``baseline_frac``
    of valid epochs -- the reference epoch -- before taking the RMS. Without this
    a pure monotonic trend would show a spurious error equal to the trend's mean.
    """
    v = valid & np.isfinite(dvv)
    if v.sum() < 10:
        return float("nan")
    d, tr, dd = dvv[v], truth[v], days[v]
    cut = np.quantile(dd, baseline_frac)
    base = dd <= cut
    if base.sum() < 2:
        base = np.ones_like(dd, bool)
    d0 = d - d[base].mean()
    tr0 = tr - tr[base].mean()
    return float(np.sqrt(np.mean((d0 - tr0) ** 2)))


def compute_metrics(case_id: str, data: dict | None = None) -> dict:
    """Run the recommended pipeline (+ any probes) and return the RMS oracle."""
    recipe = CASES_BY_ID[case_id]
    d = data if data is not None else generate(case_id)
    use_case = recipe["use_case"]
    cfg = uc.recommend(use_case, **recipe.get("config", {}))
    eps = uc.eps_max(use_case)

    dvv, valid = run_pipeline(d["ccfs"], d["t"], d["fs"], cfg, eps_max=eps)
    res = {"config": _jsonable(cfg), "eps_max": eps,
           "rms": _rms(dvv, d["truth"], d["days"], valid)}

    probes = []
    for p in recipe.get("probes", []):
        pcfg = uc.recommend(use_case, **p.get("config", {}))
        truth = d["truth_deep"] if p.get("truth") == "deep" else d["truth"]
        pdvv, pvalid = run_pipeline(d["ccfs"], d["t"], d["fs"], pcfg, eps_max=eps)
        probes.append({"label": p["label"], "config": _jsonable(pcfg),
                       "truth": p.get("truth", "shallow"),
                       "rms": _rms(pdvv, truth, d["days"], pvalid)})
    if probes:
        res["probes"] = probes
    return res


def _jsonable(cfg: dict) -> dict:
    """Tuples (band, window) -> lists so the config round-trips through JSON."""
    return {k: (list(v) if isinstance(v, tuple) else v) for k, v in cfg.items()}


# ---------------------------------------------------------------------------
# Manifest read / write
# ---------------------------------------------------------------------------
def regenerate_manifest() -> dict:
    """Recompute every case's expected metrics and rewrite ``manifest.json``."""
    cases = []
    for c in CASES:
        d = generate(c["id"])
        m = compute_metrics(c["id"], d)
        entry = {
            "id": c["id"], "kind": c["kind"], "use_case": c["use_case"],
            "split": case_split(c), "visibility": case_visibility(c),
            "years": c["years"], "snr": c["snr"], "seed": c["seed"],
            "cadence": c.get("cadence", 1), "decorr": c.get("decorr", 0.0),
            "rms_rel_tol": c["rms_rel_tol"], "n_days": int(len(d["days"])),
            "expected": m,
        }
        if "note" in c:
            entry["note"] = c["note"]
        cases.append(entry)
        print(f"  {c['id']:<24} rms={m['rms']:.5f}"
              + (f"  (+{len(m['probes'])} probe)" if "probes" in m else ""))
    manifest = {"version": MANIFEST_VERSION, "cases": cases}
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def expected_metrics(case_id: str) -> dict:
    for c in load_manifest()["cases"]:
        if c["id"] == case_id:
            return c["expected"]
    raise KeyError(case_id)


def main() -> int:
    print(f"Regenerating golden manifest ({len(CASES)} cases) -> {MANIFEST}")
    regenerate_manifest()
    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
