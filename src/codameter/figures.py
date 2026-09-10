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
import json
import platform
import subprocess
from collections.abc import Callable, Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

from ._version import __version__

__all__ = [
    "EXTERNAL",
    "SLOW",
    "generators",
    "figure_arrays",
    "figure_inventory",
    "save_figure",
    "build_all_figures",
]

#: Figures the paper includes that are produced outside this repository.
EXTERNAL = (
    "realdata_1_validation",
    "realdata_2_interferograms",
    "realdata_3_warmup",
)
#: Generators that take minutes rather than seconds.
SLOW = {"demo_10_deviations", "demo_11_multiverse", "demo_12_bayes"}

Generator = Callable[[], tuple[Any, dict[str, Any], dict[str, Any]]]


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parent,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    sha = out.stdout.strip()
    return sha if out.returncode == 0 and sha else None


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
    np.savez_compressed(outdir / f"{name}.npz", **arrays)
    meta: dict[str, Any] = {
        "figure": name,
        "generator": generator,
        "codameter_version": __version__,
        "git_commit": _git_commit(),
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
    return gens


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
    wanted = list(gens) if only is None else list(only)
    unknown = sorted(set(wanted) - set(gens))
    if unknown:
        raise KeyError(f"unknown figure(s): {unknown}; known: {sorted(gens)}")
    if skip_slow:
        wanted = [n for n in wanted if n not in SLOW]
    apply_style()
    written = []
    for name in wanted:
        desc, gen = gens[name]
        print(f"[{name}] {desc}", flush=True)
        fig, arrays, meta = gen()
        written.append(
            save_figure(
                fig, outdir, name, generator=desc, extra_arrays=arrays, extra_meta=meta
            )
        )
        plt.close(fig)
        print(f"  wrote {written[-1]} (+ .npz, .json)", flush=True)
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default="literature/figs", help="output directory")
    ap.add_argument("--only", default=None, help="comma-separated figure names")
    ap.add_argument("--skip-slow", action="store_true", help=f"skip {sorted(SLOW)}")
    ap.add_argument("--list", action="store_true", help="list figures and exit")
    args = ap.parse_args(argv)
    if args.list:
        for name, (desc, _) in generators().items():
            print(f"{name:<28} {desc}{'  (slow)' if name in SLOW else ''}")
        for name in EXTERNAL:
            print(f"{name:<28} external; see literature/figs/SOURCES.md")
        return 0
    only = [s.strip() for s in args.only.split(",")] if args.only else None
    build_all_figures(args.out, only=only, skip_slow=args.skip_slow)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
