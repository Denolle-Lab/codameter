r"""Shardable config-sweep benchmark: recovery RMS over case x config grids.

The scientific payload is embarrassingly parallel and deterministic: for every
golden case (:mod:`codameter.golden`) and every processing config in a grid
built around that case's recommended choice (:mod:`codameter.use_cases`), run the
pipeline on the known synthetic via :func:`codameter.golden.recover` (which
aggregates the channels of a multi-channel case) and record how well the
recovered dv/v tracks the truth. The result is one row per ``(case, config)``
cell: a sensitivity map of which deviations cost how much.

This module is built to fan out across a cluster (AWS Batch array on Fargate, or
any array runner):

- ``--shard k/N`` deterministically partitions the ordered work list, so array
  task ``k`` of ``N`` computes its slice and nothing else. Round-robin, so load
  is even even when some configs (moving/inversion references) are far slower.
- ``--jobs`` runs the shard's cells across local vCPUs.
- ``--out`` takes a local dir or an ``s3://`` prefix; each shard writes one
  ``shard-<k>-of-<N>.jsonl`` so shards never collide and Batch retries are
  idempotent. ``aggregate`` merges the shard files into one table.
- ``plan`` prints the work-item and per-shard counts so you can size the array.

Run ``codameter-bench --help``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from collections.abc import Iterator
from functools import cache
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np

from . import golden
from . import use_cases as uc
from ._version import __version__
from .deviations import metrics
from .provenance import git_commit

# ---------------------------------------------------------------------------
# Config grids, built relative to each case's recommended config.
# Each grid names, per axis, how to vary it: "rec" = keep the recommended value,
# "variants" = the generator below, or an explicit list of values. band/window
# variants scale around the recommended value so the grid stays physical for the
# use case (a landslide keeps a high-frequency band; a volcano a low one).
# ---------------------------------------------------------------------------
ESTIMATORS_ALL = ["stretching (TS)", "MWCS", "WCS", "DTW"]

GRIDS: dict[str, dict[str, Any]] = {
    # Small, fast: for `plan`, tests, and smoke runs.
    "compact": {
        "estimator": ["stretching (TS)", "MWCS"],
        "band": "rec",
        "window": "rec",
        "stack": "rec",
        "reference": ["fixed", "moving"],
        "gate": [True],
    },
    # The default massive sweep: hundreds of cells per case.
    "multiverse": {
        "estimator": ESTIMATORS_ALL,
        "band": "variants",
        "window": "variants",
        "stack": [None, 1, 45],
        "reference": ["fixed", "moving", "inversion"],
        "gate": [True, False],
    },
    # Everything, for an overnight run.
    "wide": {
        "estimator": ESTIMATORS_ALL,
        "band": "variants",
        "window": "variants",
        "stack": [None, 1, 5, 20, 60],
        "reference": ["fixed", "moving", "inversion"],
        "gate": [True, False],
    },
}


def _band_variants(band) -> list[tuple[float, float]]:
    lo, hi = float(band[0]), float(band[1])
    out = [(lo, hi), (lo * 0.5, hi * 0.5), (lo * 1.5, hi * 1.5)]
    # Keep physical: strictly positive and ordered.
    return [(max(a, 1e-3), b) for a, b in out if b > max(a, 1e-3)]


def _window_variants(window) -> list[tuple[float, float]]:
    a, b = float(window[0]), float(window[1])
    span = b - a
    return [(a, b), (a, a + 0.5 * span), (a, a + 1.8 * span)]


def _axis_values(rec_value, mode, generator) -> list:
    if mode == "rec":
        return [rec_value]
    if mode == "variants":
        return generator(rec_value)
    return list(mode)  # explicit list


def build_grid(case: dict, grid: str = "multiverse") -> list[dict]:
    """Return the list of configs to score for one golden ``case`` under ``grid``.

    The grid is built around that case's recommended config, so each application
    keeps a physical band/window. For a depth-targeted (``two_layer``) case the
    band axis is the two *depth* bands rather than variants around one: the whole
    question there is whether a config selects the right depth, so the sweep must
    be able to choose either layer (and be scored for choosing wrong).
    """
    if grid not in GRIDS:
        raise ValueError(f"unknown grid {grid!r}; known: {sorted(GRIDS)}")
    spec = GRIDS[grid]
    use_case = case["use_case"]
    # For a depth case, `config` carries the target band, so `rec` is the correct
    # answer for this case rather than the application default.
    rec = uc.recommend(use_case, **case.get("config", {}))
    if case.get("two_layer"):
        shallow, deep = golden._depth_bands(use_case)
        bands = [shallow, deep]
    else:
        bands = _axis_values(rec["band"], spec["band"], _band_variants)
    windows = _axis_values(rec["window"], spec["window"], _window_variants)
    stacks = [
        rec["stack"] if s is None else s
        for s in _axis_values(rec["stack"], spec["stack"], None)
    ]
    configs = []
    for est, band, window, stack, ref, gate in product(
        spec["estimator"], bands, windows, stacks, spec["reference"], spec["gate"]
    ):
        configs.append(
            {
                "estimator": est,
                "band": tuple(band),
                "window": tuple(window),
                "stack": int(stack),
                "reference": ref,
                "gate": bool(gate),
            }
        )
    return configs


# ---------------------------------------------------------------------------
# Work list + sharding
# ---------------------------------------------------------------------------
def work_items(case_ids: list[str], grid: str) -> list[tuple[str, int, dict]]:
    """Every ``(case_id, config_index, config)`` cell, in a stable order."""
    items = []
    for cid in case_ids:
        for i, cfg in enumerate(build_grid(golden.CASES_BY_ID[cid], grid)):
            items.append((cid, i, cfg))
    return items


def shard(items: list, k: int, n: int) -> list:
    """Round-robin slice ``k`` of ``n`` (``0 <= k < n``)."""
    if not (0 <= k < n):
        raise ValueError(f"shard index {k} out of range for {n} shards")
    return items[k::n]


def parse_shard(spec: str | None) -> tuple[int, int]:
    """Parse ``--shard k/N``; fall back to AWS Batch array env; default 0/1.

    AWS Batch array jobs set ``AWS_BATCH_JOB_ARRAY_INDEX``; pass ``--shards N``
    (or ``CODAMETER_SHARDS``) as the array size and the index is read from the
    environment, so the same image runs every array task.
    """
    if spec:
        k, n = spec.split("/")
        return int(k), int(n)
    idx = os.environ.get("AWS_BATCH_JOB_ARRAY_INDEX") or os.environ.get(
        "CODAMETER_SHARD_INDEX"
    )
    cnt = os.environ.get("CODAMETER_SHARDS")
    if idx is not None and cnt is not None:
        return int(idx), int(cnt)
    return 0, 1


# ---------------------------------------------------------------------------
# Scoring one cell
# ---------------------------------------------------------------------------
@cache
def _case(case_id: str) -> dict:
    """Load a case's arrays once per process (deterministic, disk-cached)."""
    return golden.generate(case_id)


def score_cell(case_id: str, config_index: int, cfg: dict) -> dict:
    """Score one ``(case, config)`` cell into a JSON-serializable row."""
    case = golden.CASES_BY_ID[case_id]
    use_case = case["use_case"]
    row = {
        "case_id": case_id,
        "use_case": use_case,
        "grade": case["grade"],
        "config_index": config_index,
        "estimator": cfg["estimator"],
        "band": list(cfg["band"]),
        "window": list(cfg["window"]),
        "stack": cfg["stack"],
        "reference": cfg["reference"],
        "gate": cfg["gate"],
        "target": case.get("target"),
        "eps_max": uc.eps_max(use_case),
        "codameter_version": __version__,
        # The generator digest and commit pin the synthesis code the golden
        # arrays were built with (audit S-RP.4); check_shards refuses to merge
        # rows whose digests differ.
        "generator_hash": golden._generator_hash(),
        "git_commit": git_commit(),
    }
    try:
        d = _case(case_id)
        # golden.recover is the single scoring path: it runs the pipeline per
        # channel and aggregates for multi-channel (hard) cases, and falls back
        # to the plain pipeline for single-channel ones.
        dvv, valid = golden.recover(d, cfg, row["eps_max"])
        m = metrics(dvv, d["truth"], d["days"], valid)
        row.update(
            rms=golden._rms(dvv, d["truth"], d["days"], valid),
            drop_err=m["drop_err"],
            n_valid=int(np.sum(valid)),
            ok=True,
            error=None,
        )
    except Exception as exc:  # a bad cell must not kill the shard
        row.update(rms=None, drop_err=None, n_valid=0, ok=False, error=str(exc))
    return row


def _score_star(args):
    return score_cell(*args)


# ---------------------------------------------------------------------------
# Sweep driver
# ---------------------------------------------------------------------------
def run_sweep(
    *,
    case_ids: list[str],
    grid: str,
    k: int,
    n: int,
    jobs: int = 1,
    progress_every: int = 200,
) -> list[dict]:
    """Score this shard's cells and return the rows (unwritten)."""
    items = shard(work_items(case_ids, grid), k, n)
    # Pre-generate the shard's unique cases to disk once, so parallel workers
    # read the cache rather than racing to write it.
    for cid in dict.fromkeys(c for c, _, _ in items):
        golden.generate(cid)

    rows: list[dict] = []
    if jobs and jobs > 1:
        from concurrent.futures import ProcessPoolExecutor

        with ProcessPoolExecutor(max_workers=jobs) as ex:
            for i, row in enumerate(ex.map(_score_star, items, chunksize=4), 1):
                rows.append(row)
                if i % progress_every == 0:
                    print(f"  {i}/{len(items)} cells", file=sys.stderr, flush=True)
    else:
        for i, (cid, ci, cfg) in enumerate(items, 1):
            rows.append(score_cell(cid, ci, cfg))
            if i % progress_every == 0:
                print(f"  {i}/{len(items)} cells", file=sys.stderr, flush=True)
    return rows


# ---------------------------------------------------------------------------
# Output (local or s3://)
# ---------------------------------------------------------------------------
def _write_jsonl(rows: list[dict], out: str, name: str) -> str:
    """Write ``rows`` to ``<out>/<name>``; ``out`` may be a local dir or s3://."""
    body = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    return _write_text(body, out, name)


def _write_text(body: str, out: str, name: str) -> str:
    if out.startswith("s3://"):
        import tempfile

        import boto3  # optional; only needed for s3 output

        bucket, _, prefix = out[len("s3://") :].partition("/")
        key = f"{prefix.rstrip('/')}/{name}" if prefix else name
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
            fh.write(body)
            tmp = fh.name
        boto3.client("s3").upload_file(tmp, bucket, key)
        os.unlink(tmp)
        return f"s3://{bucket}/{key}"
    dest = Path(out)
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / name
    path.write_text(body)
    return str(path)


_SHARD_RE = re.compile(r"shard-(\d+)-of-(\d+)\.jsonl$")


def _read_jsonl_dir(src: str) -> Iterator[tuple[str, dict]]:
    """Yield ``(shard_file_name, row)`` for every row under ``src``."""
    if src.startswith("s3://"):
        import boto3

        bucket, _, prefix = src[len("s3://") :].partition("/")
        s3 = boto3.client("s3")
        for obj in s3.get_paginator("list_objects_v2").paginate(
            Bucket=bucket, Prefix=prefix
        ):
            for it in obj.get("Contents", []):
                if it["Key"].endswith(".jsonl"):
                    body = s3.get_object(Bucket=bucket, Key=it["Key"])["Body"].read()
                    for line in body.decode().splitlines():
                        if line.strip():
                            yield Path(it["Key"]).name, json.loads(line)
    else:
        for path in sorted(Path(src).glob("shard-*.jsonl")):
            for line in path.read_text().splitlines():
                if line.strip():
                    yield path.name, json.loads(line)


def check_shards(pairs: list[tuple[str, dict]]) -> dict:
    """Inventory a set of shard rows and list what stops them being merged.

    A merge is complete only if every shard ``k`` of the declared ``N`` is
    present, every ``(case_id, config_index)`` cell appears exactly once, and
    all rows come from one codameter version and one generator digest
    (audits SCALE-02 and S-RP.4). Retries that rewrite a shard file are fine;
    a shard appended twice is not. The commits the rows were produced at are
    listed but not required to agree: a digest pins the synthesis code, a
    commit only the tree it was run from.
    """
    names = sorted({n for n, _ in pairs})
    ks: set[int] = set()
    ns: set[int] = set()
    unparsed = []
    for n in names:
        m = _SHARD_RE.search(n)
        if not m:
            unparsed.append(n)
            continue
        ks.add(int(m.group(1)))
        ns.add(int(m.group(2)))
    problems = []
    if unparsed:
        problems.append(f"unrecognised shard file name(s): {unparsed}")
    if len(ns) > 1:
        problems.append(f"shard files declare different shard counts: {sorted(ns)}")
    n_shards = next(iter(ns)) if len(ns) == 1 else 0
    missing = sorted(set(range(n_shards)) - ks)
    if missing:
        problems.append(f"missing shard(s) {missing} of {n_shards}")
    cells = Counter((r.get("case_id"), r.get("config_index")) for _, r in pairs)
    dups = sorted(c for c, k in cells.items() if k > 1)
    if dups:
        problems.append(
            f"duplicate cell(s): {dups[:10]}{' ...' if len(dups) > 10 else ''}"
        )
    versions = sorted({str(r.get("codameter_version")) for _, r in pairs})
    if len(versions) > 1:
        problems.append(f"rows from different codameter versions: {versions}")
    n_no_hash = sum(1 for _, r in pairs if not r.get("generator_hash"))
    if n_no_hash:
        problems.append(f"{n_no_hash} row(s) carry no generator digest")
    hashes = sorted(
        {str(r["generator_hash"]) for _, r in pairs if r.get("generator_hash")}
    )
    if len(hashes) > 1:
        problems.append(f"rows from different generator digests: {hashes}")
    commits = sorted({str(r.get("git_commit")) for _, r in pairs})
    return {
        "n_shards": n_shards,
        "shards_present": sorted(ks),
        "missing": missing,
        "duplicate_cells": len(dups),
        "codameter_versions": versions,
        "generator_hashes": hashes,
        "git_commits": commits,
        "n_rows": len(pairs),
        "unique_cells": len(cells),
        "problems": problems,
        "complete": not problems,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _all_case_ids(selector: str | None) -> list[str]:
    if not selector or selector == "all":
        return [c["id"] for c in golden.CASES]
    return [s.strip() for s in selector.split(",") if s.strip()]


def _cmd_plan(args) -> int:
    case_ids = _all_case_ids(args.cases)
    items = work_items(case_ids, args.grid)
    k, n = parse_shard(args.shard)
    per = [len(shard(items, i, n)) for i in range(n)]
    print(
        f"grid={args.grid}  cases={len(case_ids)}  configs/case="
        f"{len(build_grid(golden.CASES_BY_ID[case_ids[0]], args.grid))}"
    )
    print(
        f"total cells={len(items)}  shards={n}  "
        f"cells/shard: min={min(per)} max={max(per)}"
    )
    return 0


def _cmd_sweep(args) -> int:
    case_ids = _all_case_ids(args.cases)
    k, n = parse_shard(args.shard)
    print(
        f"sweep grid={args.grid} shard={k}/{n} cases={len(case_ids)} jobs={args.jobs}",
        file=sys.stderr,
    )
    rows = run_sweep(case_ids=case_ids, grid=args.grid, k=k, n=n, jobs=args.jobs)
    name = f"shard-{k:05d}-of-{n:05d}.jsonl"
    where = _write_jsonl(rows, args.out, name)
    ok = sum(r["ok"] for r in rows)
    print(f"wrote {len(rows)} rows ({ok} ok) -> {where}", file=sys.stderr)
    return 0


def _cmd_aggregate(args) -> int:
    pairs = list(_read_jsonl_dir(args.src))
    if not pairs:
        print("no shard rows found", file=sys.stderr)
        return 1
    inventory = check_shards(pairs)
    allow_partial = bool(getattr(args, "allow_partial", False))
    for problem in inventory["problems"]:
        print(f"aggregate: {problem}", file=sys.stderr)
    fatal = [
        p
        for p in inventory["problems"]
        if not (allow_partial and p.startswith("missing shard"))
    ]
    if fatal:
        print(
            "aggregate: refusing to merge; --allow-partial accepts missing "
            "shards only, never duplicates or mixed versions",
            file=sys.stderr,
        )
        return 1
    rows = [r for _, r in pairs]
    where = _write_jsonl(rows, args.out, "sweep.jsonl")
    inventory["n_ok"] = sum(bool(r.get("ok")) for r in rows)
    _write_text(
        json.dumps(inventory, indent=1) + "\n", args.out, "aggregate_manifest.json"
    )
    # Compact per-case summary: best config by RMS.
    best: dict[str, dict] = {}
    for r in rows:
        if not r.get("ok") or r.get("rms") is None:
            continue
        cur = best.get(r["case_id"])
        if cur is None or r["rms"] < cur["rms"]:
            best[r["case_id"]] = r
    print(f"aggregated {len(rows)} rows -> {where}")
    for cid in sorted(best):
        b = best[cid]
        print(
            f"  {cid:<24} best rms={b['rms'] * 100:.4f}%  "
            f"{b['estimator']} band={b['band']} ref={b['reference']}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="codameter-bench", description=__doc__.split("\n")[0]
    )
    sub = p.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--grid", default="multiverse", choices=sorted(GRIDS))
    common.add_argument(
        "--cases", default="all", help="'all' or a comma-separated list of case ids"
    )
    common.add_argument(
        "--shard",
        default=None,
        help="k/N; else read AWS_BATCH_JOB_ARRAY_INDEX + CODAMETER_SHARDS",
    )

    sp = sub.add_parser("plan", parents=[common], help="count work items / shards")
    sp.set_defaults(func=_cmd_plan)

    ss = sub.add_parser("sweep", parents=[common], help="score this shard's cells")
    ss.add_argument("--out", required=True, help="local dir or s3:// prefix")
    ss.add_argument(
        "--jobs",
        type=int,
        default=int(os.environ.get("CODAMETER_JOBS", "1")),
        help="parallel worker processes for this shard",
    )
    ss.set_defaults(func=_cmd_sweep)

    sa = sub.add_parser("aggregate", help="merge shard-*.jsonl into one table")
    sa.add_argument("--src", required=True, help="dir or s3:// prefix of shard files")
    sa.add_argument("--out", required=True, help="local dir or s3:// prefix")
    sa.add_argument(
        "--allow-partial",
        action="store_true",
        help="merge even if shards are missing (recorded in "
        "aggregate_manifest.json); duplicates still refuse",
    )
    sa.set_defaults(func=_cmd_aggregate)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
