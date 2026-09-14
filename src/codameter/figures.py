"""One driver for every generated figure in the paper, with a numerical sidecar.

Run::

    python -m codameter.figures --out literature/figs            # everything
    python -m codameter.figures --out literature/figs --skip-slow
    python -m codameter.figures --out literature/figs --only demo_12_bayes
    python -m codameter.figures --list

For each figure ``<name>`` this writes ``<name>.png``, ``<name>.npz`` (every
plotted array: line x/y, image arrays and extents, collection vertices and
offsets, bar rectangles, plus the generator's own result arrays under
``data/``) and ``<name>.json`` (generator, codameter version, git commit,
timestamp, library versions, and an inventory of axes and arrays). The
sidecars are what a caption or a sentence in the manuscript should be
computed from, so plotted and quoted numbers come from one output
(audit findings REP-01, FIG-02, SCI-07).

The three real-data figures (:data:`EXTERNAL`) are not produced here; their
provenance is recorded in ``literature/figs/SOURCES.md``.
"""

from __future__ import annotations

import argparse
import dataclasses
import functools
import json
import platform
import warnings
from collections.abc import Callable, Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

from ._version import __version__
from .errors import MissingInputs
from .provenance import git_commit, git_dirty

__all__ = [
    "EXTERNAL",
    "SLOW",
    "generators",
    "figure_arrays",
    "compact_array",
    "figure_inventory",
    "save_figure",
    "build_all_figures",
]

#: Figures the paper includes that are produced outside this repository.
EXTERNAL = (
    "realdata_2_interferograms",
    "realdata_3_warmup",
)
#: Generated figures whose inputs are not tracked by git (skipped with a
#: message where the inputs are absent).
NEEDS_DATA = {"realdata_1_validation"}
#: Generators that take minutes rather than seconds.
SLOW = {"demo_10_deviations", "demo_11_multiverse", "demo_12_bayes"}
#: float64 arrays with more elements than this are stored as float32 in the
#: sidecar (seven significant digits); smaller arrays are stored exactly.
LARGE_ARRAY = 50_000

Generator = Callable[[], tuple[Any, dict[str, Any], dict[str, Any]]]


_git_commit = git_commit  # kept for callers of the old private names
_git_dirty = git_dirty


#: Modules whose source enters the generator digest: every figure builder
#: lives in one of them, so a change to any of them changes the digest.
_DIGEST_MODULES = (
    "figures",
    "synthetic_demo",
    "deviations",
    "uq_bayes",
    "uq_measurement",
    "gate1",
)


@functools.lru_cache(maxsize=1)
def generator_digest() -> str:
    """Short digest of the package version and the figure-generating sources.
    Computed once per process (the sources do not change during a build).

    Recorded in every sidecar so that a figure can be matched to the exact
    generator code, as :func:`codameter.golden._generator_hash` does for the
    golden datasets; two sidecars with the same digest were produced by the
    same figure code whatever the commit says.
    """
    import hashlib

    h = hashlib.sha1(__version__.encode())
    here = Path(__file__).resolve().parent
    for mod in _DIGEST_MODULES:
        h.update((here / f"{mod}.py").read_bytes())
    return h.hexdigest()[:12]


def _jsonable(obj: Any) -> Any:
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return _jsonable(dataclasses.asdict(obj))
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.generic):
        return obj.item()
    return obj


# ---------------------------------------------------------------------------
# Extracting what a figure actually plots.
# ---------------------------------------------------------------------------
def figure_arrays(fig) -> dict[str, np.ndarray]:
    """Every plotted array in ``fig``, keyed ``ax{i}/{artist}{j}/{field}``."""
    out: dict[str, np.ndarray] = {}
    for i, ax in enumerate(fig.axes):
        for j, ln in enumerate(ax.get_lines()):
            out[f"ax{i}/line{j}/x"] = np.asarray(ln.get_xdata(orig=False), float)
            out[f"ax{i}/line{j}/y"] = np.asarray(ln.get_ydata(orig=False), float)
        for j, im in enumerate(ax.get_images()):
            out[f"ax{i}/image{j}"] = np.asarray(im.get_array())
            out[f"ax{i}/image{j}/extent"] = np.asarray(im.get_extent(), float)
        for j, coll in enumerate(ax.collections):
            offsets = np.asarray(coll.get_offsets(), float)
            if offsets.size:
                out[f"ax{i}/collection{j}/offsets"] = offsets
            paths = coll.get_paths()
            if paths:
                verts = [np.asarray(p.vertices, float) for p in paths]
                out[f"ax{i}/collection{j}/vertices"] = np.concatenate(verts, axis=0)
                out[f"ax{i}/collection{j}/path_lengths"] = np.array(
                    [len(v) for v in verts], int
                )
        for j, patch in enumerate(ax.patches):
            if hasattr(patch, "get_x") and hasattr(patch, "get_height"):
                out[f"ax{i}/patch{j}/xywh"] = np.array(
                    [
                        patch.get_x(),
                        patch.get_y(),
                        patch.get_width(),
                        patch.get_height(),
                    ],
                    float,
                )
    return out


def compact_array(a: np.ndarray) -> np.ndarray:
    """Store large float64 arrays as float32 (see :data:`LARGE_ARRAY`)."""
    a = np.asarray(a)
    if a.dtype == np.float64 and a.size > LARGE_ARRAY:
        return a.astype(np.float32)
    return a


def figure_inventory(fig) -> list[dict[str, Any]]:
    """Axes titles, labels and artist labels, aligned with :func:`figure_arrays`."""
    inv = []
    for i, ax in enumerate(fig.axes):
        inv.append(
            {
                "axes": f"ax{i}",
                "title": ax.get_title(),
                "xlabel": ax.get_xlabel(),
                "ylabel": ax.get_ylabel(),
                "lines": [ln.get_label() for ln in ax.get_lines()],
                "images": len(ax.get_images()),
                "collections": [c.get_label() for c in ax.collections],
                "patches": len(ax.patches),
            }
        )
    return inv


def save_figure(
    fig,
    outdir: str | Path,
    name: str,
    *,
    generator: str,
    extra_arrays: dict[str, Any] | None = None,
    extra_meta: dict[str, Any] | None = None,
) -> Path:
    """Write ``<name>.png`` with its ``.npz`` and ``.json`` sidecars."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    png = outdir / f"{name}.png"
    fig.savefig(png, bbox_inches="tight")
    arrays: dict[str, Any] = dict(figure_arrays(fig))
    for k, v in (extra_arrays or {}).items():
        arrays[f"data/{k}"] = np.asarray(v)
    arrays = {k: compact_array(v) for k, v in arrays.items()}
    np.savez_compressed(outdir / f"{name}.npz", **arrays)
    meta: dict[str, Any] = {
        "figure": name,
        "generator": generator,
        "codameter_version": __version__,
        "git_commit": _git_commit(),
        "git_dirty": _git_dirty(),
        "generator_digest": generator_digest(),
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "matplotlib": matplotlib.__version__,
        "axes": figure_inventory(fig),
        "arrays": sorted(arrays),
    }
    meta.update(_jsonable(extra_meta or {}))
    (outdir / f"{name}.json").write_text(json.dumps(meta, indent=1) + "\n")
    return png


# ---------------------------------------------------------------------------
# The registry: name -> generator returning (fig, extra_arrays, extra_meta).
# ---------------------------------------------------------------------------
def _gen_demo_10():
    from . import deviations as dv

    rows, _ = dv.oat_effects()
    fig = dv.fig_deviation_ranking(rows)
    return fig, {}, {"oat_rows": _jsonable(rows)}


def _gen_demo_11():
    from . import deviations as dv

    mv = dv.multiverse()
    fig = dv.fig_multiverse_full(mv)
    arrays = {k: mv[k] for k in ("curves", "rms", "drop") if k in mv}
    meta = {k: v for k, v in mv.items() if k not in arrays}
    return fig, arrays, {"multiverse": meta}


def _gen_demo_12():
    from . import uq_bayes as ub

    res, run = ub._build_bayes()
    fig = ub._fig_bayes(res, run)
    arrays = {
        "times_days": res.times_days,
        "mu_mean": res.mu_mean,
        "mu_lo": res.mu_lo,
        "mu_hi": res.mu_hi,
        "mu_cov": res.mu_cov,
        "Cd": res.Cd,
        "total_std": res.total_std,
        "method_std": res.method_std,
        "within_std": res.within_std,
        "members": run.members,
        "within_sigma": run.within_sigma,
    }
    if run.truth is not None:
        arrays["truth"] = run.truth
    meta = {
        "bayes": {
            "tau": res.tau,
            "s": res.s,
            "corr_length_days": res.corr_length_days,
            "n_eff": res.n_eff,
            "n_epochs": int(res.times_days.size),
            "labels": list(run.labels),
        }
    }
    return fig, arrays, meta


def _gen_realdata_1():
    from .gate1 import fig_gate1_comparison

    fig = fig_gate1_comparison()
    return fig, dict(fig.codameter_arrays), dict(fig.codameter_meta)


def generators() -> dict[str, tuple[str, Generator]]:
    """Every generated figure: ``name -> (generator description, callable)``."""
    from . import synthetic_demo as sd

    gens: dict[str, tuple[str, Generator]] = {}
    for name, builder in sd.FIGURES.items():

        def _gen(b=builder):
            return b(), {}, {}

        gens[name] = (f"codameter.synthetic_demo.{builder.__name__}", _gen)
    gens["demo_10_deviations"] = (
        "codameter.deviations.oat_effects + fig_deviation_ranking",
        _gen_demo_10,
    )
    gens["demo_11_multiverse"] = (
        "codameter.deviations.multiverse + fig_multiverse_full",
        _gen_demo_11,
    )
    gens["demo_12_bayes"] = (
        "codameter.uq_bayes._build_bayes + _fig_bayes",
        _gen_demo_12,
    )
    gens["realdata_1_validation"] = (
        "codameter.gate1.fig_gate1_comparison (needs paper/data/gate1/dvv2y)",
        _gen_realdata_1,
    )
    return gens


def _select(
    only: Iterable[str] | None,
    skip_slow: bool,
    gens: dict[str, tuple[str, Generator]] | None = None,
) -> list[str]:
    gens = generators() if gens is None else gens
    wanted = list(gens) if only is None else list(only)
    unknown = sorted(set(wanted) - set(gens))
    if unknown:
        raise KeyError(f"unknown figure(s): {unknown}; known: {sorted(gens)}")
    if skip_slow:
        wanted = [n for n in wanted if n not in SLOW]
    return wanted


def build_all_figures(
    outdir: str | Path,
    *,
    only: Iterable[str] | None = None,
    skip_slow: bool = False,
) -> list[Path]:
    """Render the selected figures with sidecars; returns the PNG paths."""
    import matplotlib.pyplot as plt

    from .synthetic_demo import apply_style

    gens = generators()
    wanted = _select(only, skip_slow, gens)
    apply_style()
    written = []
    for name in wanted:
        desc, gen = gens[name]
        print(f"[{name}] {desc}", flush=True)
        try:
            fig, arrays, meta = gen()
        except MissingInputs as exc:
            print(f"  skipped: {exc}", flush=True)
            continue
        written.append(
            save_figure(
                fig, outdir, name, generator=desc, extra_arrays=arrays, extra_meta=meta
            )
        )
        plt.close(fig)
        print(f"  wrote {written[-1]} (+ .npz, .json)", flush=True)
    return written


def _max_abs(x: np.ndarray) -> float:
    """Largest finite magnitude in ``x`` (0.0 when there is none).

    Allocates one temporary the size of ``x`` (the masked magnitudes), not a
    concatenation of both arrays being compared.
    """
    if x.size == 0:
        return 0.0
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN input
        m = np.nanmax(np.where(np.isfinite(x), np.abs(x), np.nan))
    return float(m) if np.isfinite(m) else 0.0


def compare_sidecar(arrays: dict[str, Any], npz_path: Path, *, rtol: float = 1e-6):
    """Compare freshly generated arrays with a committed ``.npz`` sidecar.

    Returns a list of human-readable differences (empty when they agree).
    Floating arrays agree when every entry is within ``rtol`` of the stored
    value or within ``rtol`` times the largest magnitude in either array (so the
    rounding noise of an entry that is zero up to platform arithmetic, such
    as the zero-change point of a sweep, does not count as a difference).
    Large float64 arrays are compared at float32 precision, the precision the
    sidecar stores them at (:data:`LARGE_ARRAY`); NaNs must match in position.
    """
    diffs: list[str] = []
    if not npz_path.exists():
        return [f"no committed sidecar at {npz_path}"]
    with np.load(npz_path, allow_pickle=False) as z:
        stored = {k: z[k] for k in z.files}
    fresh = {k: compact_array(np.asarray(v)) for k, v in arrays.items()}
    for k in sorted(set(stored) | set(fresh)):
        if k not in stored:
            diffs.append(f"{k}: new array not in the sidecar")
            continue
        if k not in fresh:
            diffs.append(f"{k}: in the sidecar but no longer generated")
            continue
        a, b = stored[k], fresh[k]
        if a.shape != b.shape:
            diffs.append(f"{k}: shape {a.shape} in sidecar, {b.shape} generated")
            continue
        if a.dtype.kind in "fc" and b.dtype.kind in "fc":
            tol = max(rtol, 1e-6 if a.dtype == np.float32 else rtol)
            scale = max(_max_abs(a), _max_abs(b))
            if not np.allclose(a, b, rtol=tol, atol=tol * scale, equal_nan=True):
                with np.errstate(
                    invalid="ignore", divide="ignore"
                ), warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN ratio
                    denom = np.maximum(np.maximum(np.abs(a), np.abs(b)), tol * scale)
                    rel = np.nanmax(np.abs(a - b) / denom)
                if np.isfinite(rel):
                    diffs.append(
                        f"{k}: values differ (max relative difference {rel:.3g})"
                    )
                else:
                    diffs.append(f"{k}: values differ only in NaN placement")
        elif not np.array_equal(a, b):
            diffs.append(f"{k}: values differ")
    return diffs


def check_all_figures(
    outdir: str | Path,
    *,
    only: Iterable[str] | None = None,
    skip_slow: bool = False,
    rtol: float = 1e-6,
) -> dict[str, list[str]]:
    """Regenerate the selected figures in memory and diff their arrays against
    the committed sidecars in ``outdir``; returns ``{name: differences}``."""
    import matplotlib.pyplot as plt

    from .synthetic_demo import apply_style

    gens = generators()
    outdir = Path(outdir)
    apply_style()
    report: dict[str, list[str]] = {}
    for name in _select(only, skip_slow, gens):
        desc, gen = gens[name]
        print(f"[{name}] {desc}", flush=True)
        try:
            fig, arrays, meta = gen()
        except MissingInputs as exc:
            print(f"  skipped: {exc}", flush=True)
            continue
        all_arrays: dict[str, Any] = dict(figure_arrays(fig))
        for k, v in (arrays or {}).items():
            all_arrays[f"data/{k}"] = np.asarray(v)
        plt.close(fig)
        report[name] = compare_sidecar(all_arrays, outdir / f"{name}.npz", rtol=rtol)
        status = "ok" if not report[name] else f"{len(report[name])} difference(s)"
        print(f"  {status}", flush=True)
        for d in report[name]:
            print(f"    {d}", flush=True)
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default="literature/figs", help="output directory")
    ap.add_argument("--only", default=None, help="comma-separated figure names")
    ap.add_argument("--skip-slow", action="store_true", help=f"skip {sorted(SLOW)}")
    ap.add_argument("--list", action="store_true", help="list figures and exit")
    ap.add_argument(
        "--check",
        action="store_true",
        help="regenerate in memory and diff against the committed sidecars; "
        "exit 1 on any difference",
    )
    ap.add_argument(
        "--rtol",
        type=float,
        default=1e-6,
        help="relative tolerance for --check (float32-stored arrays use at least 1e-6)",
    )
    args = ap.parse_args(argv)
    if args.list:
        for name, (desc, _) in generators().items():
            print(f"{name:<28} {desc}{'  (slow)' if name in SLOW else ''}")
        for name in EXTERNAL:
            print(f"{name:<28} external; see literature/figs/SOURCES.md")
        return 0
    only = [s.strip() for s in args.only.split(",")] if args.only else None
    if args.check:
        report = check_all_figures(
            args.out, only=only, skip_slow=args.skip_slow, rtol=args.rtol
        )
        bad = {k: v for k, v in report.items() if v}
        print(
            f"checked {len(report)} figure(s): {len(report) - len(bad)} match, "
            f"{len(bad)} differ"
        )
        return 1 if bad else 0
    build_all_figures(args.out, only=only, skip_slow=args.skip_slow)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
