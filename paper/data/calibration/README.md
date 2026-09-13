# Coverage calibration runs

Produced by `python -m codameter.calibration` (see its module docstring). Each
JSON holds `settings`, `seeds`, per-realisation `results` and the aggregate
`summary` that `paper/build_calibration_table.py` turns into
`paper/calibration_table.tex`. The table builder reads `locked_*.json` only.

| File | Invocation | Notes |
|---|---|---|
| `locked_clean_n200.json` | `--n 200 --start-seed 2000 --scenario clean --jobs 6` | 2026-09-13, iteration-3 rerun with the held-out-half coverage, the two-chain split R-hat and the corrected correlation-length fit. Every in-sample statistic (member and posterior coverages, s, tau, bias, RMSE, prior shares) is bit-identical to the 2026-09-10 run it replaces; only `corr_length_days` and `n_eff` changed with the fit. |
| `locked_shared_source_n200.json` | `--scenario shared_source`, same n, seeds and jobs | pending rerun; until then it carries the 2026-09-10 run without the new diagnostics and with the withdrawn correlation-length fit |
| `locked_clock_drift_n200.json` | `--scenario clock_drift`, same n, seeds and jobs | same as above |
| `pilot_*_n20.json` | `--n 20 --start-seed 1000` | pilots used to fix the acceptance margin before the locked runs; not used by the table |

Environment for the locked runs: single-threaded BLAS
(`OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1`), six worker
processes, wall time about two hours per scenario on a 10-core laptop.

Provenance caveat: `git_commit` in a JSON is the HEAD at run time. The
iteration-3 reruns were produced from the working tree of the P1 branch before
its commit, so their `git_commit` field names the base commit (the P0 merge,
c0f91f1) and not the commit whose code produced them; the code that ran is the
one committed with these files (issue #39). A dirty-tree flag and a source
digest are added to this record in P3 (issue #41).
