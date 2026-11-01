"""Re-run of review/evidence/downstream_probes.py against the revised code (INV-02)."""

import json
import warnings
from pathlib import Path

import numpy as np
from codameter.inverse.linear_fit import PredictorMatrix, linear_fit
from codameter.uq_measurement import global_reference_inversion

p = PredictorMatrix(X=np.ones((20, 1)), parameter_names=["amplitude"])
r = linear_fit(
    -np.ones(20) * 0.1, p, sigma_dvv=1.0, parameter_bounds={"amplitude": (0.0, np.inf)}
)
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    g = global_reference_inversion(
        np.array([0]), np.array([1]), np.array([0.01]), np.array([0.001]), 3
    )
assert r.posterior.cov is not None and r.at_bound is not None
out = {
    "bounded_fit_mean": r.posterior.mean.tolist(),
    "bounded_fit_covariance": r.posterior.cov.tolist(),
    "bounded_fit_at_bound": [bool(b) for b in r.at_bound],
    "disconnected_reference_solution": [None if np.isnan(x) else x for x in g.dvv],
    "disconnected_reference_std": [None if np.isnan(x) else x for x in g.sigma],
    "n_components": g.n_components,
    "warning": str(w[0].message) if w else None,
}
path = Path(__file__).resolve().parent / "downstream_probes_after.json"
path.write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
