"""Git provenance helpers shared by the figure driver and the benchmark.

Kept free of plotting imports so that a benchmark row can record the commit
without importing matplotlib.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            cwd=_HERE,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


def git_commit() -> str | None:
    """Full SHA of HEAD in the repository this package is imported from (None outside git)."""
    out = _git("rev-parse", "HEAD")
    sha = (out or "").strip()
    return sha or None


def git_dirty() -> bool | None:
    """True when tracked files under ``src/`` differ from HEAD (None outside git).

    The pathspec is the parent of the package directory, so every tracked
    source under ``src/`` counts, not only ``src/codameter``. A record whose
    ``git_commit`` names a commit but whose ``git_dirty`` is true was produced
    by code that commit does not contain (audit S-RP.1).
    """
    out = _git("status", "--porcelain", "--untracked-files=no", "--", str(_HERE.parent))
    if out is None:
        return None
    return bool(out.strip())
