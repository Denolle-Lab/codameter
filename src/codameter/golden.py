r"""Golden synthetic datasets for dv/v processing: a graded, seeded corpus.

Three difficulty **grades**, ten cases each (30 total), spanning the monitoring
applications so a grade covers a realistic range rather than one scenario:

- **easy** -- a pure seasonal signal at high SNR, single channel. The recommended
  (best-practice) config should recover it cleanly.
- **medium** -- a transient (coseismic-style) drop with logarithmic, only partial
  recovery, plus more measurement noise (lower SNR).
- **hard** -- a *multi-channel*, *depth- and frequency-dependent* problem. A
  shallow (high-frequency) layer carries a coseismic drop-and-heal plus a full
  hydrological seasonal cycle; a deep (low-frequency) layer carries a long-term
  trend. Each case targets one depth, so the measurement band must match it: the
  band selects the depth. Low SNR with waveform decorrelation; the channels are
  measured independently and aggregated to a network dv/v.

Every case has an exactly known ground-truth dv/v(t) (imposed by stretching a
band-limited decaying coda in lapse time), so any departure of a recovered series
is an artefact of the processing, not of nature.

Design: the committed artefact is ``tests/data/golden/manifest.json`` -- the
recipes plus expected metrics, not the arrays. A multi-year (multi-channel) CCF
stack is large and fully determined by its seed, so arrays are regenerated on
demand and cached under ``tests/data/golden/cache/`` (gitignored).

Consumers: :mod:`tests.test_golden` (regression oracle), the ``codameter-advisor``
skill (live validation), and the FrugalMind ``dvv_processing`` suites
(:mod:`codameter.frugalmind`). All score through :func:`recover`, so a single
code path handles both single- and multi-channel cases.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np

from . import use_cases as uc
from .deviations import run_pipeline
from .synthetic_demo import YEAR_D, _days, _seasonal, daily_ccfs, make_coda

DATA_DIR = Path(__file__).resolve().parents[2] / "tests" / "data" / "golden"
MANIFEST = DATA_DIR / "manifest.json"
CACHE_DIR = DATA_DIR / "cache"
MANIFEST_VERSION = 2


# ---------------------------------------------------------------------------
# Per-application signal amplitudes (fractional dv/v) and timescales. These set
# the physical scale of each motif; they stay within the application's eps_max.
# ---------------------------------------------------------------------------
AMP = {
    "volcano":          {"seasonal": 0.0010, "drop": -0.0040, "trend": -0.0015, "tau": 90.0,  "phase": 60.0},
    "earthquake_fault": {"seasonal": 0.0006, "drop": -0.0025, "trend": -0.0010, "tau": 160.0, "phase": 30.0},
    "landslide":        {"seasonal": 0.0100, "drop": -0.0300, "trend": -0.0050, "tau": 60.0,  "phase": 120.0},
    "groundwater":      {"seasonal": 0.0015, "drop": -0.0020, "trend": -0.0012, "tau": 120.0, "phase": 250.0},
    "cryosphere":       {"seasonal": 0.0300, "drop": -0.0150, "trend": -0.0040, "tau": 45.0,  "phase": 200.0},
    "geothermal":       {"seasonal": 0.0005, "drop": -0.0060, "trend": -0.0100, "tau": 120.0, "phase": 30.0},
}


def _step_heal(days: np.ndarray, app: str, onset_frac: float = 0.5) -> np.ndarray:
    """A sharp drop at ~``onset_frac`` of the record with logarithmic partial heal."""
    a = AMP[app]
    onset = onset_frac * float(days[-1])
    co = days >= onset
    dt = (days[co] - onset).astype(float)
    out = np.zeros(len(days), float)
    out[co] = a["drop"] * (0.35 + 0.65 * np.exp(-dt / a["tau"]))
    return out


def _motif_seasonal(days: np.ndarray, app: str) -> np.ndarray:
    return _seasonal(days, AMP[app]["seasonal"], AMP[app]["phase"])


def _motif_transient(days: np.ndarray, app: str) -> np.ndarray:
    # drop + heal, plus a muted seasonal so it is not unrealistically flat.
    return _step_heal(days, app) + 0.25 * _motif_seasonal(days, app)


def _motif_composite(days: np.ndarray, app: str) -> np.ndarray:
    # transient + full hydrological seasonal + a long-term linear trend.
    a = AMP[app]
    trend = a["trend"] * np.clip((days - 0.15 * days[-1]) / (0.8 * days[-1]), 0, 1)
    return _step_heal(days, app) + _motif_seasonal(days, app) + trend


MOTIF = {"seasonal": _motif_seasonal, "transient": _motif_transient,
         "composite": _motif_composite}


# ---------------------------------------------------------------------------
# Depth- and frequency-dependent medium (the hard grade). The shallow layer
# carries the near-surface response (coseismic drop + heal + full hydrological
# seasonal); the deep layer carries the long-term trend with a muted seasonal.
# The two layers live in separated frequency bands, so the measurement *band
# selects the depth*: a shallow (high-frequency) band recovers the shallow truth,
# a deep (low-frequency) band recovers the deep truth.
# ---------------------------------------------------------------------------
def _truth_shallow(days: np.ndarray, app: str) -> np.ndarray:
    return _step_heal(days, app) + _motif_seasonal(days, app)


def _truth_deep(days: np.ndarray, app: str) -> np.ndarray:
    a = AMP[app]
    trend = a["trend"] * np.clip((days - 0.15 * days[-1]) / (0.8 * days[-1]), 0, 1)
    return trend + 0.3 * _motif_seasonal(days, app)


def _depth_bands(app: str) -> tuple[tuple[float, float], tuple[float, float]]:
    """Split an application's coda band into separated shallow (high) / deep (low)
    sub-bands, each safely inside the generated content."""
    glo, ghi = uc.synth_params(app)["gen_band"]
    gm = (glo * ghi) ** 0.5
    shallow = (round(gm * 1.6, 3), round(ghi * 0.9, 3))
    deep = (round(glo * 1.1, 3), round(gm * 0.6, 3))
    return shallow, deep


# ---------------------------------------------------------------------------
# Grades and case construction. Each grade cycles through the applications so it
# spans volcano / fault / aquifer / glacier / reservoir at that difficulty.
# ---------------------------------------------------------------------------
GRADES = {
    "easy":   {"motif": "seasonal",  "snr": (8.0, 12.0), "channels": 1, "decorr": 0.00,
               "years": 3.0, "split": "validation", "rms_rel_tol": 0.35},
    "medium": {"motif": "transient", "snr": (3.0, 5.0),  "channels": 1, "decorr": 0.05,
               "years": 3.0, "split": "validation", "rms_rel_tol": 0.45},
    "hard":   {"motif": "depth", "snr": (2.0, 4.0),  "channels": 4, "decorr": 0.20,
               "years": 2.5, "split": "test", "rms_rel_tol": 0.60},
}

# 10 application slots per grade (the 6 applications, some repeated).
APP_CYCLE = ["volcano", "earthquake_fault", "landslide", "groundwater",
             "cryosphere", "geothermal", "volcano", "groundwater",
             "landslide", "earthquake_fault"]

_SEED_BASE = {"easy": 100, "medium": 200, "hard": 300}


def _build_cases() -> list[dict]:
    cases = []
    for grade, spec in GRADES.items():
        snr_lo, snr_hi = spec["snr"]
        for i, app in enumerate(APP_CYCLE):
            snr = round(float(np.interp(i, [0, len(APP_CYCLE) - 1], [snr_hi, snr_lo])), 2)
            case = {
                "id": f"{grade}-{app}-{i + 1:02d}",
                "grade": grade, "use_case": app, "motif": spec["motif"],
                "snr": snr, "seed": _SEED_BASE[grade] + i,
                "channels": spec["channels"], "decorr": spec["decorr"],
                "years": spec["years"], "split": spec["split"],
                "rms_rel_tol": spec["rms_rel_tol"],
            }
            if grade == "hard":
                # Depth- and frequency-dependent: the case targets one depth, and
                # the recommended config's band must match it. Targets alternate.
                shallow_band, deep_band = _depth_bands(app)
                target = "shallow" if i % 2 == 0 else "deep"
                case["two_layer"] = True
                case["target"] = target
                case["config"] = {"band": shallow_band if target == "shallow" else deep_band}
                case["note"] = (
                    "The medium is depth-dependent: a shallow near-surface layer "
                    "(coseismic drop + hydrological seasonal) sits above a deep layer "
                    "(long-term trend). "
                    + ("You must resolve the SHALLOW near-surface response."
                       if target == "shallow" else
                       "You must resolve the DEEP long-term trend.")
                    + " The band selects the depth."
                )
            cases.append(case)
    return cases


CASES: list[dict] = _build_cases()
CASES_BY_ID = {c["id"]: c for c in CASES}


def representative_case(use_case: str, grade: str = "easy") -> str:
    """A matched case id for an application (default the first easy case).

    Used by the advisor and the sweep to pull a synthetic that matches a user's
    application without hardcoding ids.
    """
    key = uc.resolve(use_case)
    for c in CASES:
        if c["use_case"] == key and c["grade"] == grade:
            return c["id"]
    for c in CASES:                       # fall back to any grade
        if c["use_case"] == key:
            return c["id"]
    raise KeyError(f"no golden case for use case {use_case!r}")


# Back-compat alias: application -> a representative (easy) case.
MAINSTREAM_BY_USE_CASE = {
    app: representative_case(app) for app in {c["use_case"] for c in CASES}
}


def case_split(recipe: dict) -> str:
    return recipe.get("split", "validation")


def case_visibility(recipe: dict) -> str:
    """Synthetic and seed-reproducible, so public by default."""
    return recipe.get("visibility", "public")


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------
def _build(recipe: dict) -> dict:
    """Regenerate the arrays for one case deterministically from its recipe."""
    app = recipe["use_case"]
    sp = uc.synth_params(app)
    fs, gen = sp["fs"], sp["gen_band"]
    days = _days(recipe["years"])
    seed, snr = recipe["seed"], recipe["snr"]
    decorr = recipe.get("decorr", 0.0)
    nchan = int(recipe.get("channels", 1))

    t, coda0 = make_coda(maxlag_s=sp["maxlag_s"], fs=fs, band=gen,
                         t_coda_s=sp["t_coda_s"], seed=0)
    out: dict = {"fs": fs, "days": days, "use_case": app, "grade": recipe["grade"],
                 "t": t}

    if recipe.get("two_layer"):
        # Depth-dependent medium: shallow (high-freq) and deep (low-freq) layers,
        # each carrying its own dv/v. Every channel sums both layers; the band
        # (set by the recommended config) selects which depth is recovered. The
        # scored truth is the targeted layer.
        shallow_band, deep_band = _depth_bands(app)
        truth_shallow = _truth_shallow(days, app)
        truth_deep = _truth_deep(days, app)
        chans = []
        for c in range(nchan):
            _, cod_s = make_coda(maxlag_s=sp["maxlag_s"], fs=fs, band=shallow_band,
                                 t_coda_s=sp["t_coda_s"], seed=2 * c)
            _, cod_d = make_coda(maxlag_s=sp["maxlag_s"], fs=fs, band=deep_band,
                                 t_coda_s=sp["t_coda_s"], seed=2 * c + 1)
            chans.append(daily_ccfs(t, [cod_s, cod_d], [truth_shallow, truth_deep],
                                    fs=fs, snr=snr, decorr=decorr, gen_band=gen,
                                    seed=seed + 7 * c))
        out["channels"] = np.stack(chans)
        out["ccfs"] = out["channels"].mean(axis=0)
        out["truth"] = truth_shallow if recipe["target"] == "shallow" else truth_deep
        out["truth_other"] = truth_deep if recipe["target"] == "shallow" else truth_shallow
        return out

    truth = MOTIF[recipe["motif"]](days, app)
    out["truth"] = truth
    if nchan > 1:
        # Independent cross-component channels: distinct coda + distinct noise,
        # sharing the medium's truth. Measured per channel, aggregated later.
        codas = [coda0] + [make_coda(maxlag_s=sp["maxlag_s"], fs=fs, band=gen,
                                     t_coda_s=sp["t_coda_s"], seed=c)[1]
                           for c in range(1, nchan)]
        chans = [daily_ccfs(t, [cod], [truth], fs=fs, snr=snr, decorr=decorr,
                            gen_band=gen, seed=seed + 7 * c)
                 for c, cod in enumerate(codas)]
        out["channels"] = np.stack(chans)
        out["ccfs"] = out["channels"].mean(axis=0)  # a 2D view for plotting
    else:
        out["ccfs"] = daily_ccfs(t, [coda0], [truth], fs=fs, snr=snr,
                                 decorr=decorr, gen_band=gen, seed=seed)
    return out


def recover(d: dict, cfg: dict, eps_max: float):
    """Recover dv/v(t) for a case under ``cfg``; the single scoring entry point.

    Single-channel cases run the pipeline directly. Multi-channel cases run the
    pipeline on each channel and aggregate to a network dv/v by averaging the
    per-channel series (the "average the per-component dv/v" convention).
    """
    if "channels" in d and np.ndim(d["channels"]) == 3:
        per = []
        for c in range(d["channels"].shape[0]):
            dvv_c, val_c = run_pipeline(d["channels"][c], d["t"], d["fs"], cfg,
                                        eps_max=eps_max)
            per.append(np.where(val_c, dvv_c, np.nan))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN columns
            dvv = np.nanmean(np.vstack(per), axis=0)
        return dvv, np.isfinite(dvv)
    return run_pipeline(d["ccfs"], d["t"], d["fs"], cfg, eps_max=eps_max)


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
def _recipe_hash(recipe: dict) -> str:
    """Short digest of a recipe, so editing it invalidates the cached arrays."""
    import hashlib

    blob = json.dumps(recipe, sort_keys=True, default=str)
    return hashlib.sha1(blob.encode()).hexdigest()[:8]


def generate(case_id: str, *, cache: bool = True) -> dict:
    """Return the arrays for a case: ``{ccfs, t, days, truth, fs, use_case, grade}``
    plus ``channels`` (3D) for multi-channel cases.

    Deterministic in the seed. Cached to ``cache/<id>-<recipe_hash>.npz`` (the hash
    busts the cache when a recipe changes). ``regenerate_manifest`` uses
    ``cache=False`` so a synthesis-*code* change (not captured by the hash) never
    scores against stale arrays.
    """
    recipe = CASES_BY_ID[case_id]
    cache_file = CACHE_DIR / f"{case_id}-{_recipe_hash(recipe)}.npz"
    if cache and cache_file.exists():
        z = np.load(cache_file, allow_pickle=False)
        d = {k: z[k] for k in z.files}
        d["fs"] = float(d["fs"])
        d["use_case"] = str(d["use_case"])
        d["grade"] = str(d["grade"])
        return d
    d = _build(recipe)
    if cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        # Downcast the large CCF arrays to float32 to keep the cache small; the
        # lapse/day/truth axes stay float64.
        payload = {"t": d["t"], "days": d["days"], "truth": d["truth"],
                   "ccfs": np.asarray(d["ccfs"], np.float32),
                   "fs": np.asarray(d["fs"]),
                   "use_case": np.asarray(d["use_case"]),
                   "grade": np.asarray(d["grade"])}
        if "channels" in d:
            payload["channels"] = np.asarray(d["channels"], np.float32)
        if "truth_other" in d:
            payload["truth_other"] = d["truth_other"]
        np.savez_compressed(cache_file, **payload)
    return d


# ---------------------------------------------------------------------------
# Metrics oracle
# ---------------------------------------------------------------------------
def _rms(dvv, truth, days, valid, baseline_frac: float = 0.2) -> float:
    """Baseline-aligned RMS error of a recovered dv/v against the truth.

    A dv/v estimate is relative to a reference epoch, so its DC offset is not
    observable. We remove, from both series, their mean over the earliest
    ``baseline_frac`` of valid epochs before taking the RMS, or a pure trend would
    show a spurious error equal to its mean.
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


def _jsonable(cfg: dict) -> dict:
    """Tuples (band, window) -> lists so the config round-trips through JSON."""
    return {k: (list(v) if isinstance(v, tuple) else v) for k, v in cfg.items()}


def compute_metrics(case_id: str, data: dict | None = None) -> dict:
    """Recover with the recommended config and return the RMS oracle."""
    recipe = CASES_BY_ID[case_id]
    d = data if data is not None else generate(case_id)
    app = recipe["use_case"]
    cfg = uc.recommend(app, **recipe.get("config", {}))
    eps = uc.eps_max(app)
    dvv, valid = recover(d, cfg, eps)
    res = {"config": _jsonable(cfg), "eps_max": eps,
           "rms": _rms(dvv, d["truth"], d["days"], valid)}
    if "truth_other" in d:
        # The error a config would incur by recovering the WRONG depth layer:
        # the "clearly wrong" anchor for scoring depth-band selection.
        allv = np.ones(len(d["days"]), bool)
        res["rms_wrong_layer"] = _rms(d["truth_other"], d["truth"], d["days"], allv)
    return res


# ---------------------------------------------------------------------------
# Manifest read / write
# ---------------------------------------------------------------------------
def regenerate_manifest() -> dict:
    """Recompute every case's expected metrics and rewrite ``manifest.json``."""
    cases = []
    for c in CASES:
        d = generate(c["id"], cache=False)          # always from current code
        m = compute_metrics(c["id"], d)
        entry = {
            "id": c["id"], "grade": c["grade"], "use_case": c["use_case"],
            "motif": c["motif"], "split": case_split(c),
            "visibility": case_visibility(c), "years": c["years"], "snr": c["snr"],
            "seed": c["seed"], "channels": c["channels"], "decorr": c["decorr"],
            "rms_rel_tol": c["rms_rel_tol"], "n_days": int(len(d["days"])),
            "expected": m,
        }
        if c.get("two_layer"):
            entry["two_layer"] = True
            entry["target"] = c["target"]
        cases.append(entry)
        print(f"  {c['id']:<26} ch={c['channels']} snr={c['snr']:<4} "
              f"rms={m['rms']:.5f}")
    manifest = {"version": MANIFEST_VERSION, "grades": list(GRADES),
                "cases": cases}
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
    print(f"Regenerating golden manifest ({len(CASES)} cases, "
          f"{len(GRADES)} grades) -> {MANIFEST}")
    regenerate_manifest()
    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
