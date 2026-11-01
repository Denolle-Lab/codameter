"""Exceptions shared across modules (kept apart so ``python -m`` runs of a
module never see two copies of a class)."""

from __future__ import annotations


class MissingInputs(RuntimeError):
    """A generator's inputs are not available on this machine (data not tracked)."""
