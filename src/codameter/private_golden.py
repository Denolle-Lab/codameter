#!/usr/bin/env python3
"""Build a *hidden* golden evaluation set with secret truth parameters.

Why this exists
---------------
The ground-truth dv/v of a golden case is a pure function of its ``amp`` numbers
(amplitude, phase, drop, healing timescale, trend, onset). In the public repo
those numbers come from the published ``golden.AMP`` table, so the truth can be
regenerated from public source alone -- no seed required. Hiding the arrays or
the seeds therefore hides nothing.

This script draws a fresh ``amp`` block per case from a **secret seed** and bakes
it into each recipe. The resulting corpus cannot be reconstructed from the public
package: an agent would have to actually measure dv/v to score.

Output (write it somewhere private; never commit it):

    <out>/cases.json      the hidden recipes, each with its secret `amp`
    <out>/manifest.json   the frozen expected metrics for those recipes

Use it by pointing codameter at the directory::

    export CODAMETER_GOLDEN_DIR=/path/to/hidden-golden
    python -c "from . import golden; print(len(golden.CASES))"

Usage (works from a pip install, which is how the eval CI regenerates it)::

    python -m codameter.private_golden --secret "$CODAMETER_GOLDEN_SECRET" \
        --out ./hidden-golden [--jitter 0.35]

The secret is the only thing you must keep safe: the same secret reproduces the
same hidden set, a different secret gives a different one.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from . import golden

# Truth parameters that get randomized. `onset_frac` moves the coseismic step, so
# even the event time is unknown; `phase` moves the seasonal peak.
JITTERED = ("seasonal", "drop", "trend", "tau", "phase")


def _rng_for(secret: str, case_id: str) -> np.random.Generator:
    """Deterministic per-case RNG derived from the secret (never from the case seed)."""
    h = hashlib.sha256(f"{secret}:{case_id}".encode()).digest()
    return np.random.default_rng(int.from_bytes(h[:8], "big"))


def secret_amp(case: dict, secret: str, jitter: float) -> dict:
    """A secret `amp` block for one case: the public values, multiplicatively
    jittered, plus a randomized event onset."""
    rng = _rng_for(secret, case["id"])
    base = golden.AMP[case["use_case"]]
    amp = {}
    for k in JITTERED:
        # log-uniform factor in [1/(1+jitter), 1+jitter]: keeps the sign and the
        # order of magnitude physical, but the exact value unknowable.
        f = float(np.exp(rng.uniform(-np.log1p(jitter), np.log1p(jitter))))
        amp[k] = float(base[k]) * f
    amp["phase"] = float(rng.uniform(0.0, 365.25))     # seasonal peak anywhere
    amp["onset_frac"] = float(rng.uniform(0.35, 0.65))  # event time unknown
    return amp


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--secret", required=True,
                    help="secret string; the same secret reproduces the same set")
    ap.add_argument("--out", type=Path, required=True, help="output directory")
    ap.add_argument("--jitter", type=float, default=0.35,
                    help="multiplicative spread on the truth amplitudes (default 0.35)")
    ap.add_argument("--exclude-public", action="store_true", default=True,
                    help="drop the public sample ids from the hidden set")
    args = ap.parse_args(argv)

    cases = [dict(c) for c in golden._build_cases()]
    if args.exclude_public:
        cases = [c for c in cases if c["id"] not in golden.PUBLIC_SAMPLE_IDS]

    for c in cases:
        c["amp"] = secret_amp(c, args.secret, args.jitter)
        c["visibility"] = "private"

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "cases.json").write_text(
        json.dumps({"cases": cases}, indent=2, default=str) + "\n")
    print(f"wrote {len(cases)} hidden cases -> {args.out/'cases.json'}")

    # Freeze the oracle for exactly these recipes, by pointing golden at the new
    # directory and regenerating. Done in a subprocess-free way: reload the module
    # state against the new DATA_DIR.
    import importlib
    import os

    os.environ["CODAMETER_GOLDEN_DIR"] = str(args.out.resolve())
    importlib.reload(golden)
    assert len(golden.CASES) == len(cases), (len(golden.CASES), len(cases))
    print(f"regenerating expected metrics for {len(golden.CASES)} hidden cases "
          f"(this runs the full pipeline; it takes a few minutes)")
    golden.regenerate_manifest()
    print(f"wrote {args.out/'manifest.json'}")
    print("\nNext: upload BOTH files to the private store, then point the scorer at it:")
    print(f"  export CODAMETER_GOLDEN_DIR={args.out.resolve()}")
    print("Never commit them, and never mount this directory into an agent sandbox.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
