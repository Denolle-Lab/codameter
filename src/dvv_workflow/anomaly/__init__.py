"""
Phase 5 — anomaly detection and attribution.

After the Phase 4 inversion, the residual

.. math::
    r(t) = \\delta v / v_{\\rm obs}(t) - \\delta v / v_{\\rm fit}(t)

should be approximately white noise with variance consistent with the
measurement errors. Phase 5 tests this assumption and, where it fails,
classifies the anomaly into one of five physical categories so that the
user can either revise the model (Phase 0–4) or accept the anomaly as a
genuine signal of interest (e.g. a slow-slip event, a long-term drying
trend, etc.).

Per the build plan, the workflow must **not** be framed as
"subtract and interpret residuals". The residuals are anomaly-detection
outputs only — once an anomaly is detected, it should be folded back as a
new physical channel in the next iteration of Phase 0–4, not interpreted as
a free signal.
"""
from __future__ import annotations

from .attribution import (
    attribute_anomaly,
    AnomalyCategory,
    ATTRIBUTION_CATEGORIES,
)
from .detection import (
    AnomalyReport,
    detect_anomalies,
    ljung_box_test,
    rolling_zscore,
    transient_segments,
)

__all__ = [
    "AnomalyReport",
    "detect_anomalies",
    "ljung_box_test",
    "rolling_zscore",
    "transient_segments",
    "AnomalyCategory",
    "ATTRIBUTION_CATEGORIES",
    "attribute_anomaly",
]
