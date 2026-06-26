r"""
Processing-choice uncertainty for :math:`\delta v / v` — a generative model.

:mod:`codameter.uq_measurement` gives the within-method *floor* and the
*temporal correlation* of a $\delta v/v$ series. This module adds the missing
piece: the uncertainty contributed by the **processing choices themselves** —
treated, in a Bayesian sense, as **nuisance parameters** to be sampled and
marginalised rather than fixed by fiat.

The central object is the coda **window rule** — the algorithm a group uses to
decide *which* part of the coda to measure. Three rules dominate practice and
each is encoded as a small generative model:

* ``"fixed"`` — a fixed lapse window :math:`[t_1, t_2]` (the most common
  choice), with :math:`t_1` and the length drawn from a group's habits;
* ``"envelope_pick_flatten"`` — start at the envelope **pick**, and stop when
  the log-envelope decay **flattens** into the noise floor. The end lapse is
  then *physical*, set by the coda quality factor :math:`Q_c` and the coda SNR:
  :math:`A(t)\propto e^{-\pi f t / Q_c}`, so the flattening lapse is
  :math:`t_2 = t_1 + \frac{Q_c}{\pi f}\ln(\mathrm{SNR}_0)` — it depends on
  **frequency**, which is exactly why this rule and a fixed window disagree;
* ``"moving"`` — short windows that **slide** in lapse time, sampling a range of
  scattering depths.

Sampling a processing choice :math:`c \sim p(c)` and pushing it through the
Weaver/Clarke floor (:func:`codameter.uq_measurement.weaver_stretching_error`)
gives, by the law of total variance, a **marginal** measurement variance

.. math::
    \operatorname{Var}(\delta v/v)
    = \underbrace{\mathbb{E}_c[\operatorname{Var}(\delta v/v \mid c)]}_{\text{within-choice floor}}
    + \underbrace{\operatorname{Var}_c[\mathbb{E}(\delta v/v \mid c)]}_{\text{processing-choice spread}} .

Grouping the samples **by frequency band** yields one marginal error per band —
the input the depth inversion in :mod:`codameter.uq_depth` needs to turn
frequency-resolved measurements into a depth profile with propagated error.

References
----------
- Weaver, R. L., et al. (2011). *Geophys. J. Int.*, 185, 1384-1392.
- Steegen, S., Tuerlinckx, F., Gelman, A., & Vanpaemel, W. (2016). Increasing
  transparency through a multiverse analysis. *Perspect. Psychol. Sci.*, 11,
  702-712. (The "multiverse" framing of analysis-choice uncertainty.)
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np

from .uq_measurement import weaver_stretching_error

__all__ = [
    "WINDOW_RULES",
    "ProcessingPrior",
    "ProcessingChoice",
    "flatten_end_lapse",
    "sample_processing_choices",
    "choice_floor",
    "per_band_marginal_error",
]

WINDOW_RULES = ("fixed", "envelope_pick_flatten", "moving")


@dataclass
class ProcessingPrior:
    r"""Prior over coda-measurement processing choices :math:`p(c)`.

    Each field encodes a community habit as a distribution. Defaults are
    deliberately broad — they represent *disagreement between groups*, not one
    group's preference.

    Parameters
    ----------
    bands_hz
        Candidate measurement-band centre frequencies (Hz).
    rule_weights
        Prior probability of each window rule in :data:`WINDOW_RULES`.
    start_lapse_s
        Uniform range for the coda start lapse :math:`t_1` (s).
    window_length_s
        Uniform range for the window length of the ``"fixed"`` rule (s).
    moving_length_s
        Window length of each ``"moving"`` sub-window (s).
    moving_span_s
        Lapse span over which ``"moving"`` windows slide (s).
    qc
        Coda quality factor :math:`Q_c` for the ``"envelope_pick_flatten"``
        rule.
    snr0
        Initial coda signal-to-noise ratio (sets the flattening lapse).
    coherence_at_start
        Coda correlation coefficient near the start lapse.
    coherence_decay_s
        E-folding lapse over which the coda coherence decays.
    """

    bands_hz: Sequence[float]
    rule_weights: Mapping[str, float] = field(
        default_factory=lambda: {
            "fixed": 0.5,
            "envelope_pick_flatten": 0.3,
            "moving": 0.2,
        }
    )
    start_lapse_s: tuple[float, float] = (3.0, 12.0)
    window_length_s: tuple[float, float] = (10.0, 40.0)
    moving_length_s: float = 5.0
    moving_span_s: float = 40.0
    qc: float = 40.0
    snr0: float = 80.0
    coherence_at_start: float = 0.98
    coherence_decay_s: float = 80.0

    def __post_init__(self) -> None:
        if len(self.bands_hz) == 0:
            raise ValueError("bands_hz must be non-empty")
        bad = set(self.rule_weights) - set(WINDOW_RULES)
        if bad:
            raise ValueError(f"unknown window rules: {sorted(bad)}")
        if sum(self.rule_weights.values()) <= 0:
            raise ValueError("rule_weights must sum to a positive value")
        if not 0 < self.start_lapse_s[0] < self.start_lapse_s[1]:
            raise ValueError("start_lapse_s must be an increasing positive range")


@dataclass(frozen=True)
class ProcessingChoice:
    """One sampled processing configuration."""

    rule: str
    f_center_hz: float
    t1_s: float
    t2_s: float
    cc: float


def flatten_end_lapse(t1_s: float, f_center_hz: float, qc: float, snr0: float) -> float:
    r"""Lapse at which the log-envelope decay flattens into the noise floor.

    From the coda amplitude decay :math:`A(t) = A_0\,e^{-\pi f t / Q_c}`, the
    measurable coda ends when :math:`A` reaches the noise level, i.e. when
    :math:`\pi f (t_2 - t_1)/Q_c = \ln \mathrm{SNR}_0`:

    .. math::
        t_2 = t_1 + \frac{Q_c}{\pi f}\,\ln(\mathrm{SNR}_0).

    This is the "stop where ``log(A)``–``t`` flattens" rule, made explicit. Note
    the **frequency dependence**: high-frequency coda decays away sooner, so this
    rule yields a *shorter* window than a fixed one at high ``f`` and a longer
    one at low ``f`` — a systematic disagreement a fixed window cannot see.
    """
    if qc <= 0 or snr0 <= 1 or f_center_hz <= 0:
        raise ValueError("require qc>0, snr0>1, f_center_hz>0")
    return float(t1_s + (qc / (np.pi * f_center_hz)) * np.log(snr0))


def _coherence(center_s: float, prior: ProcessingPrior) -> float:
    cc = prior.coherence_at_start * np.exp(-center_s / prior.coherence_decay_s)
    return float(np.clip(cc, 0.6, 0.999))


def sample_processing_choices(
    prior: ProcessingPrior,
    n_samples: int,
    rng: np.random.Generator,
) -> list[ProcessingChoice]:
    r"""Draw ``n_samples`` processing choices :math:`c \sim p(c)`.

    Each draw selects a window rule, a band, and the rule's parameters, then
    derives the coda window :math:`[t_1, t_2]` from the rule's generative model
    (see :func:`flatten_end_lapse` for the envelope rule). This is the Monte
    Carlo over the analysis "multiverse" that marginalisation needs.
    """
    if n_samples < 1:
        raise ValueError("n_samples must be >= 1")
    rules = list(prior.rule_weights)
    weights = np.array([prior.rule_weights[r] for r in rules], dtype=float)
    weights = weights / weights.sum()
    bands = np.asarray(prior.bands_hz, dtype=float)

    out: list[ProcessingChoice] = []
    for _ in range(n_samples):
        rule = str(rng.choice(rules, p=weights))
        f = float(rng.choice(bands))
        if rule == "fixed":
            t1 = float(rng.uniform(*prior.start_lapse_s))
            t2 = t1 + float(rng.uniform(*prior.window_length_s))
        elif rule == "envelope_pick_flatten":
            # start at the envelope pick (early, tightly drawn), end at flattening
            t1 = float(
                rng.uniform(prior.start_lapse_s[0], prior.start_lapse_s[0] + 2.0)
            )
            t2 = flatten_end_lapse(t1, f, prior.qc, prior.snr0)
        elif rule == "moving":
            # a short window sliding somewhere along the coda
            t1 = float(
                rng.uniform(
                    prior.start_lapse_s[0], prior.start_lapse_s[0] + prior.moving_span_s
                )
            )
            t2 = t1 + prior.moving_length_s
        else:  # pragma: no cover - guarded by ProcessingPrior
            raise ValueError(f"unknown rule {rule!r}")
        cc = _coherence(0.5 * (t1 + t2), prior)
        out.append(ProcessingChoice(rule=rule, f_center_hz=f, t1_s=t1, t2_s=t2, cc=cc))
    return out


def choice_floor(choice: ProcessingChoice) -> float:
    """Within-choice Weaver/Clarke standard error for one processing choice."""
    return float(
        weaver_stretching_error(choice.cc, choice.f_center_hz, choice.t1_s, choice.t2_s)
    )


def per_band_marginal_error(
    choices: Sequence[ProcessingChoice],
    band_bias: Mapping[float, float] | None = None,
) -> dict[float, dict[str, float]]:
    r"""Marginal :math:`\delta v / v` error per frequency band.

    Groups the sampled choices by band and applies the law of total variance:
    the **within-choice** variance is the mean squared Weaver floor; the
    **processing-choice** variance is the spread of the (optional) per-choice
    systematic ``band_bias`` plus the floor's own variability across choices.
    The returned ``total`` is the marginal standard error that the depth
    inversion uses as the per-band measurement uncertainty.

    Parameters
    ----------
    choices
        Sampled processing choices (typically from
        :func:`sample_processing_choices`).
    band_bias
        Optional mapping ``f_center -> systematic offset`` used to inject a
        known per-band methodological bias for demonstration; if omitted, the
        processing-choice variance is estimated from the floor spread alone.

    Returns
    -------
    dict
        ``{f_center: {"within": .., "processing": .., "total": .., "n": ..}}``.
    """
    by_band: dict[float, list[ProcessingChoice]] = {}
    for c in choices:
        by_band.setdefault(c.f_center_hz, []).append(c)

    result: dict[float, dict[str, float]] = {}
    for f, group in by_band.items():
        floors = np.array([choice_floor(c) for c in group], dtype=float)
        within_var = float(np.mean(floors**2))
        # processing-choice variance: spread of the per-choice central estimate.
        # Without reprocessing we proxy it by the spread of the floors (choices
        # that yield different precisions also yield different estimates); a
        # supplied band_bias adds a known systematic component.
        proc_var = float(np.var(floors, ddof=1)) if floors.size > 1 else 0.0
        if band_bias is not None and f in band_bias:
            proc_var += float(band_bias[f]) ** 2
        result[f] = {
            "within": within_var**0.5,
            "processing": proc_var**0.5,
            "total": (within_var + proc_var) ** 0.5,
            "n": float(len(group)),
        }
    return result
