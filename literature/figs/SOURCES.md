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

| `realdata_1_validation` | `codameter.gate1.fig_gate1_comparison`: needs the untracked daily products under `paper/data/gate1/dvv2y/` (skipped with a message where they are absent); every plotted array is in the sidecar |

Every `.json` sidecar records `git_commit`, `git_dirty` (true when tracked
files under `src/` differed from that commit when the figure was made) and
`generator_digest` (a digest of the package version and the figure-generating
modules, so two sidecars with the same digest came from the same figure code).
`python -m codameter.figures --check [--skip-slow]` regenerates the figures in
memory and reports any array that differs from the committed sidecar; the
`paper` workflow runs it on every pull request to the manuscript branch.

## Produced outside this repository

`realdata_2_interferograms.png` and `realdata_3_warmup.png` come from the
noisepy-dvv-cloud Gate 1 run (CI.LJR / CI.RXH / CI.ARV, 2018-2019; see
`paper/data/gate1/README.md`). Their inputs are the daily correlations of that
run, which are not archived here, so they are committed as produced. The
comparison figure (`realdata_1_validation`) used to be produced there as well;
it is now generated in this repository from the archived daily products and
`paper/data/gate1/comparison.json`. The Gate 1 run commit and `--use-case`
are to be pinned in `paper/data/gate1/README.md` (issue #46).
Until then these three figures cannot be regenerated from this checkout.
