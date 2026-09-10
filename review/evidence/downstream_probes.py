"""Reproduce constrained and disconnected uncertainty audit cases."""
import json
from pathlib import Path

import numpy as np
from codameter.inverse.linear_fit import PredictorMatrix, linear_fit
from codameter.uq_measurement import global_reference_inversion

p = PredictorMatrix(X=np.ones((20, 1)), parameter_names=["amplitude"])
r = linear_fit(
    -np.ones(20) * 0.1, p, sigma_dvv=1.0, parameter_bounds={"amplitude": (0.0, np.inf)}
)
g = global_reference_inversion(
    np.array([0]), np.array([1]), np.array([0.01]), np.array([0.001]), 3
)
out = {
    "bounded_fit_mean": r.posterior.mean.tolist(),
    "bounded_fit_covariance": r.posterior.cov.tolist(),
    "disconnected_reference_solution": g.dvv.tolist(),
    "disconnected_reference_std": g.sigma.tolist(),
}
path = Path(__file__).resolve().parent / "downstream_probes.json"
path.write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
