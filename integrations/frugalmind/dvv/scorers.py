"""Scorer registry for the dv/v suite (FrugalMind family convention).

FrugalMind rebuilds a scorer from a JSON-serializable ``scorer_spec`` via each
suite family's ``scorers.make_scorer_from_spec``. For dv/v that logic lives in
codameter (it must regenerate the hidden synthetic and run the pipeline), so we
re-export it here to satisfy the convention and keep the JSONL self-contained.

Recognised names: ``dvv_recovery`` (config task) and ``dvv_series_regression``
(series task). Both require ``codameter`` to be importable at scoring time.
"""
from __future__ import annotations

from codameter.frugalmind import make_scorer_from_spec  # noqa: F401

__all__ = ["make_scorer_from_spec"]
