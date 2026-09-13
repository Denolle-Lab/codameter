# Figure sources

Every generated figure in this directory is written by one driver,

    python -m codameter.figures --out literature/figs

which also writes `<name>.npz` (every plotted array plus the generator's
result arrays under `data/`) and `<name>.json` (generator, codameter version,
git commit, timestamp, library versions, axes and array inventory). Numbers
quoted in the manuscript about a figure should be computed from that figure's
sidecar, not re-derived elsewhere. `python -m codameter.figures --list`
prints the registry. `paper/build.py --figures` runs the driver.

| Figure | Generator |
|---|---|
| `demo_1` to `demo_9`, `demo_13` to `demo_18` | `codameter.synthetic_demo.FIGURES` (one builder each) |
| `demo_10_deviations` | `codameter.deviations.oat_effects` + `fig_deviation_ranking` (slow) |
| `demo_11_multiverse` | `codameter.deviations.multiverse` + `fig_multiverse_full` (slow) |
| `demo_12_bayes` | `codameter.uq_bayes._build_bayes` + `_fig_bayes` (slow) |

## Produced outside this repository

`realdata_1_validation.png`, `realdata_2_interferograms.png` and
`realdata_3_warmup.png` come from the noisepy-dvv-cloud Gate 1 run
(CI.LJR / CI.RXH / CI.ARV, 2018-2019; see `paper/data/gate1/README.md`).
Their inputs are the daily ensemble products under `paper/data/gate1/dvv2y/`
(not tracked by git) and the published Clements and Denolle (2022) product
under `paper/data/gate1/legacy_cd2022/`. The comparison script
(`scripts/compare_cd2022.py`) and the figure scripts live in that repository;
the commit they were run at is to be pinned here (audit finding REP-02).
Until then these three figures cannot be regenerated from this checkout.
