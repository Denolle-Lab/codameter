r"""FrugalMind-compatible view of the golden dv/v datasets.

This module exposes the seeded golden cases (:mod:`codameter.golden`) in the
shape FrugalMind's benchmark suites expect, without importing FrugalMind. It
emits ``BenchmarkRow``-shaped dicts (id, dataset_id, suite_id, version,
task_kind, split, visibility, prompt, gold, scorer_spec, metadata) and provides
deterministic, execution-based scorers that return a value in ``[0, 1]``.

A thin FrugalMind suite (see ``integrations/frugalmind/dvv/``) subclasses
``frugalmind.DenolleGroupSuite``, calls :func:`build_rows` to yield
``BenchmarkRow`` objects, and registers :func:`make_scorer_from_spec` so the
JSONL export stays self-contained. All the domain logic (synthesis, pipeline,
scoring) lives here, so codameter keeps no FrugalMind dependency and FrugalMind
keeps no dv/v physics.

Two task kinds, matching the two natural output types:

- ``param_recommendation`` -- the agent returns a processing-choice **config**
  (JSON, or a codameter snippet we parse the config out of). The scorer runs it
  through :func:`codameter.deviations.run_pipeline` on the hidden synthetic and
  scores by how well the recovered dv/v tracks the known truth. This grades the
  advisor's parameter judgment. Cheap, deterministic, no sandbox.
- ``dvv_series`` -- the agent returns the recovered **dv/v(t) series** (a JSON
  array). The scorer regresses it against the known truth within a tolerance.
  This grades the end-to-end measurement: in FrugalMind the agent runs codameter
  in the sandbox and prints the array; the scorer here does the regression.

Both are scored by recovery against ground truth, not by matching a fixed answer,
so a different-but-good pipeline scores well. Negatives are first-class: a config
that cycle-skips or picks the wrong depth band scores near zero.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any, Callable

import numpy as np

from . import golden
from . import use_cases as uc

DATASET_ID = "dvv_processing"
VERSION = "v0.1"
TASKS = ("param_recommendation", "dvv_series")

# Task kind (FrugalMind TaskKind value) per suite. Both are framed as the agent
# generating something the scorer executes/regresses, i.e. code_generation.
TASK_KIND = {
    "param_recommendation": "code_generation",
    "dvv_series": "code_generation",
}

# Scenario blurbs: describe the physical setting WITHOUT naming the recommended
# band/window, so the agent must supply the domain knowledge. The scorer grades
# on recovery, never on matching these.
SCENARIO = {
    "volcano": ("Ambient-noise monitoring of an active volcanic edifice. You want "
                "to track a slow pre-eruptive velocity change and a sharp "
                "co-eruptive drop in the shallow, crack-rich edifice (roughly the "
                "upper few km). Station pairs are available."),
    "earthquake_fault": ("Ambient-noise monitoring across a crustal fault zone. "
                         "You want to resolve a coseismic velocity drop and its "
                         "gradual, partial healing, dominated by the shallow "
                         "(top ~100 m to a few km) nonlinear site response."),
    "landslide": ("Dense-array monitoring of a clay-rich landslide body. "
                  "Inter-sensor distances are tens of meters, the failure surface "
                  "is in the top few meters to ~40 m, and you expect a large "
                  "(several percent) accelerating velocity drop before failure, on "
                  "top of a rainfall-driven seasonal swing."),
    "groundwater": ("Single-station and small-array monitoring of a shallow "
                    "aquifer, roughly the upper few hundred meters. You want the "
                    "seasonal hydrologic velocity change and a slow multi-year "
                    "drought trend."),
    "cryosphere": ("Shallow high-frequency array monitoring of a permafrost active "
                   "layer / rock glacier, top ~0-10 m. You expect a large, sharply "
                   "seasonal freeze-thaw velocity swing."),
    "geothermal": ("Monitoring of a geothermal reservoir at depths of hundreds of "
                   "meters to a few km, tracking a slow injection-driven velocity "
                   "decline. Station pairs are available."),
}

_ESTIMATORS = {"stretching (TS)", "MWCS", "WCS", "DTW", "WCC", "WTS", "WTDTW"}
_CORE_KEYS = ("estimator", "band", "window")  # the agent must choose these


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
def _scenario_text(case: dict) -> str:
    base = SCENARIO[case["use_case"]]
    note = case.get("note")
    if note:
        base = base + " Note on the data: " + note
    return base


def _param_prompt(case: dict) -> str:
    return (
        "You are configuring an ambient-noise dv/v (relative seismic velocity "
        "change) monitoring pipeline for the following setting.\n\n"
        f"{_scenario_text(case)}\n\n"
        "Choose the processing parameters. Return ONLY a JSON object with keys:\n"
        '  "estimator": one of ["stretching (TS)", "MWCS", "WCS", "DTW", "WCC", '
        '"WTS", "WTDTW"]\n'
        '  "band": [fmin_hz, fmax_hz]           # measurement frequency band\n'
        '  "window": [start_s, end_s]           # coda lapse-time window\n'
        '  "stack": integer days               # reference/substack length\n'
        '  "reference": one of ["fixed", "moving", "inversion"]\n'
        '  "gate": true or false                # drop low-coherence epochs\n\n'
        "Return only the JSON object, no prose."
    )


def _series_prompt(case: dict) -> str:
    return (
        "You are measuring an ambient-noise dv/v (relative seismic velocity "
        "change) time series for the following setting.\n\n"
        f"{_scenario_text(case)}\n\n"
        "The daily cross-correlation functions for this case are available in "
        f'codameter as golden.generate("{case["id"]}") -> {{"ccfs", "t", "days", '
        '"fs", ...}}. Choose an appropriate pipeline, recover the dv/v(t) series, '
        f'and return ONLY a JSON array of {golden.generate(case["id"])["days"].size} '
        "floats: the fractional dv/v for each day in order. No prose."
    )


# ---------------------------------------------------------------------------
# Gold + rows
# ---------------------------------------------------------------------------
def _thresholds(case_id: str) -> dict:
    """RMS scoring band for a case, from the frozen manifest + case tolerance."""
    entry = next(c for c in golden.load_manifest()["cases"] if c["id"] == case_id)
    target = float(entry["expected"]["rms"])
    tol = float(entry["rms_rel_tol"])
    good = max(target * (1.0 + tol), target + 5e-5)
    bad = max(target * 6.0, 3.0e-3)
    return {"rms_target": target, "rms_ceiling": good, "rms_bad": bad}


def _gold(case: dict, task: str) -> dict:
    g = {"case_id": case["id"], "use_case": case["use_case"], **_thresholds(case["id"])}
    if task == "dvv_series":
        d = golden.generate(case["id"])
        g["n_days"] = int(d["days"].size)
        # Anchor "clearly wrong" to the null (no-change) prediction: a returned
        # series of zeros should score ~0. For a low-amplitude target the fixed
        # rms_bad is too lenient, so use the larger of the two.
        null_rms = golden._rms(np.zeros_like(d["truth"]), d["truth"], d["days"],
                               np.ones_like(d["truth"], bool))
        if np.isfinite(null_rms) and null_rms > g["rms_ceiling"]:
            g["rms_bad"] = float(null_rms)
    return g


def build_rows(task: str, *, split: str | None = None,
               visibility: str | None = None) -> list[dict]:
    """Return BenchmarkRow-shaped dicts for one task over the golden cases.

    Filter by ``split`` ("validation"/"test") and/or ``visibility``
    ("public"/"private") to match a FrugalMind export request.
    """
    if task not in TASKS:
        raise ValueError(f"task must be one of {TASKS}; got {task!r}")
    prompt_fn = _param_prompt if task == "param_recommendation" else _series_prompt
    scorer_name = ("dvv_recovery" if task == "param_recommendation"
                   else "dvv_series_regression")
    rows = []
    for case in golden.CASES:
        if split is not None and golden.case_split(case) != split:
            continue
        if visibility is not None and golden.case_visibility(case) != visibility:
            continue
        rows.append({
            "id": f"{DATASET_ID}/{task}/{case['id']}",
            "dataset_id": DATASET_ID,
            "suite_id": task,
            "version": VERSION,
            "task_kind": TASK_KIND[task],
            "split": golden.case_split(case),
            "visibility": golden.case_visibility(case),
            "prompt": prompt_fn(case),
            "gold": _gold(case, task),
            "scorer_spec": {"name": scorer_name, "config": {}},
            "metadata": {
                "case_id": case["id"], "use_case": case["use_case"],
                "grade": case["grade"],
                "recommended_config": golden._jsonable(uc.recommend(case["use_case"])),
            },
        })
    return rows


# ---------------------------------------------------------------------------
# Parsing agent output
# ---------------------------------------------------------------------------
def _first_json(text: str, opener: str, closer: str):
    """Parse the first balanced ``opener..closer`` block in text as JSON/literal."""
    start = text.find(opener)
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == opener:
            depth += 1
        elif text[i] == closer:
            depth -= 1
            if depth == 0:
                blob = text[start:i + 1]
                for loader in (json.loads, ast.literal_eval):
                    try:
                        return loader(blob)
                    except Exception:
                        continue
                return None
    return None


def parse_config(text: str) -> dict | None:
    """Extract a processing-choice dict from agent text (JSON object or snippet)."""
    obj = _first_json(text, "{", "}")
    return obj if isinstance(obj, dict) else None


def _as_pair(v):
    if isinstance(v, (list, tuple)) and len(v) == 2:
        return (float(v[0]), float(v[1]))
    if isinstance(v, str):
        m = re.findall(r"[-+]?\d*\.?\d+", v)
        if len(m) >= 2:
            return (float(m[0]), float(m[1]))
    return None


def parse_series(text: str, n: int | None = None) -> np.ndarray | None:
    """Extract a numeric dv/v series (JSON array) from agent text."""
    arr = _first_json(text, "[", "]")
    if arr is None:
        nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", text)
        arr = [float(x) for x in nums] if nums else None
    if arr is None:
        return None
    try:
        out = np.asarray(arr, dtype=float).ravel()
    except Exception:
        return None
    if n is not None and out.size != n:
        return None
    return out


# ---------------------------------------------------------------------------
# Scorers (output_text, gold) -> float in [0, 1]
# ---------------------------------------------------------------------------
def _score_from_rms(rms: float, good: float, bad: float) -> float:
    if not np.isfinite(rms):
        return 0.0
    if rms <= good:
        return 1.0
    if rms >= bad:
        return 0.0
    return float((bad - rms) / (bad - good))


def score_param_recommendation(output_text: str, gold: dict) -> float:
    """Run the agent's config on the hidden synthetic; score by recovery RMS."""
    parsed = parse_config(output_text)
    if not parsed:
        return 0.0
    # The three scientific choices must be present; the rest fall back to the
    # use-case default so a partial-but-sound answer still runs.
    if not all(k in parsed for k in _CORE_KEYS):
        return 0.0
    cfg = dict(uc.recommend(gold["use_case"]))
    for k in uc.CONFIG_KEYS:
        if k in parsed:
            cfg[k] = parsed[k]
    band, window = _as_pair(cfg.get("band")), _as_pair(cfg.get("window"))
    if band is None or window is None or cfg.get("estimator") not in _ESTIMATORS:
        return 0.0
    cfg["band"], cfg["window"] = band, window
    d = golden.generate(gold["case_id"])
    try:
        dvv, valid = golden.recover(d, cfg, uc.eps_max(gold["use_case"]))
    except Exception:
        return 0.0
    rms = golden._rms(dvv, d["truth"], d["days"], valid)
    return _score_from_rms(rms, gold["rms_ceiling"], gold["rms_bad"])


def score_dvv_series(output_text: str, gold: dict) -> float:
    """Regress the agent's returned dv/v(t) against the known truth."""
    d = golden.generate(gold["case_id"])
    series = parse_series(output_text, n=int(gold["n_days"]))
    if series is None:
        return 0.0
    valid = np.isfinite(series)
    rms = golden._rms(series, d["truth"], d["days"], valid)
    return _score_from_rms(rms, gold["rms_ceiling"], gold["rms_bad"])


def make_scorer_from_spec(spec: dict) -> Callable[[str, Any], float]:
    """Reconstruct a scorer from a JSON-serializable spec (FrugalMind contract).

    Spec shape: ``{"name": <scorer_name>, "config": {...}}``. Recognised names:
    ``dvv_recovery`` (config task) and ``dvv_series_regression`` (series task).
    Both require codameter to be importable, since they regenerate the hidden
    synthetic from its seed and run the pipeline.
    """
    name = spec["name"]
    if name == "dvv_recovery":
        return score_param_recommendation
    if name == "dvv_series_regression":
        return score_dvv_series
    raise ValueError(f"unknown dv/v scorer {name!r}")


# ---------------------------------------------------------------------------
# Self-hosted JSONL export (mirrors frugalmind.export, no FrugalMind import)
# ---------------------------------------------------------------------------
def export_jsonl(out_dir: str | Path, *, version: str = VERSION,
                 visibility: str | None = None) -> dict:
    """Write ``<out_dir>/<dataset>/<version>/<task>.jsonl`` + a sha256 manifest.

    This lets codameter self-host the benchmark in the canonical FrugalMind
    layout. FrugalMind's own ``export-suite`` produces byte-identical rows via
    the drop-in suite, so either path yields the same dataset.
    """
    import hashlib

    target_dir = Path(out_dir) / DATASET_ID / version
    target_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for task in TASKS:
        rows = build_rows(task, visibility=visibility)
        path = target_dir / f"{task}.jsonl"
        with open(path, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        h = hashlib.sha256(path.read_bytes()).hexdigest()
        files[f"{task}.jsonl"] = {"sha256": h, "n_rows": len(rows)}
    manifest = {"dataset_id": DATASET_ID, "version": version, "files": files}
    (target_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Export the dv/v benchmark as JSONL.")
    ap.add_argument("--out", default="datasets", help="output root directory")
    ap.add_argument("--visibility", default=None, choices=[None, "public", "private"],
                    help="export only rows with this visibility")
    args = ap.parse_args(argv)
    manifest = export_jsonl(args.out, visibility=args.visibility)
    dest = Path(args.out) / DATASET_ID / VERSION
    print(f"Wrote {DATASET_ID} {VERSION} -> {dest}")
    for name, info in manifest["files"].items():
        print(f"  {name:<26} {info['n_rows']} rows  sha256={info['sha256'][:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
