"""FrugalMind benchmark suites for dv/v processing, backed by codameter.

Drop this package into a FrugalMind checkout as ``src/frugalmind_suites/dvv/``
(see ../README.md). It is a thin adapter: all synthesis, pipeline execution and
scoring live in ``codameter.frugalmind``; this file only wraps the rows in
FrugalMind's ``DenolleGroupSuite`` / ``BenchmarkRow`` contract.

Two suites, one per output type:

- ``DVVParamRecommendationSuite`` (suite_id ``param_recommendation``) -- the
  model returns a processing-choice config; the scorer runs it on the hidden
  synthetic and grades recovery of the known dv/v. This is the cheap,
  deterministic, sandbox-free suite that grades parameter judgment.
- ``DVVSeriesSuite`` (suite_id ``dvv_series``) -- the model returns the recovered
  dv/v(t) series (in FrugalMind, a ReAct agent runs codameter in the sandbox and
  prints the array); the scorer regresses it against the truth.

Both score by recovery against ground truth, so a different-but-sound pipeline
scores well and a wrong band or a cycle-skipping estimator scores near zero.
"""
from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from typing import Any

from frugalmind import DenolleGroupSuite, TaskKind
from frugalmind.export import BenchmarkRow

from codameter import frugalmind as cfm

_VALID_SPLITS = ("validation", "test")


def _env_split(explicit: str | None) -> str | None:
    """Honour FM_DVV_SPLIT when the caller passed nothing; validate when set."""
    split = explicit if explicit is not None else os.environ.get("FM_DVV_SPLIT")
    if split in (None, "", "all"):
        return None
    if split not in _VALID_SPLITS:
        raise ValueError(f"split must be one of {_VALID_SPLITS} or None; got {split!r}")
    return split


class _DVVSuite(DenolleGroupSuite):
    """Shared wiring; subclasses set ``task`` and the identity trio."""

    task: str = ""
    task_kind = TaskKind.CODE_GENERATION
    dataset_id = cfm.DATASET_ID
    version = cfm.VERSION

    def __init__(self, split: str | None = None, visibility: str | None = None) -> None:
        self.split = _env_split(split)
        self.visibility = visibility

    def _rows(self) -> list[dict]:
        return cfm.build_rows(self.task, split=self.split, visibility=self.visibility)

    def items(self) -> Iterable[tuple[str, Any, Callable[[str, Any], float]]]:
        for r in self._rows():
            yield (r["prompt"], r["gold"], cfm.make_scorer_from_spec(r["scorer_spec"]))

    def export_rows(self) -> Iterable[BenchmarkRow]:
        for r in self._rows():
            yield BenchmarkRow(**r)


class DVVParamRecommendationSuite(_DVVSuite):
    task = "param_recommendation"
    suite_id = "param_recommendation"


class DVVSeriesSuite(_DVVSuite):
    task = "dvv_series"
    suite_id = "dvv_series"


ALL_SUITES = [DVVParamRecommendationSuite(), DVVSeriesSuite()]
