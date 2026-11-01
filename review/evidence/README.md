# Audit evidence index

## Focused reviews

- [Paper sections](paper_sections.md): Abstract, Introduction, Discussion, Conclusions, Citation Diversity.
- [Methods and figures](methods_figures.md): Methods, Results, Figures/Data; visual QA.
- [Reproducibility](reproducibility.md): reconstruction, test runs, build, scaling, provenance.
- [Citation inventory](citation_inventory.json): bibliography counts and extraction.

## Executable audit cases

- [audit_probes.py](audit_probes.py) and [results](audit_probes.json): sparse scoring, advisor routes, dimensions, variance, shared bias, time semantics, cache precision.
- [downstream_probes.py](downstream_probes.py) and [results](downstream_probes.json): boundary covariance and disconnected reference graph.
- [reproduction_probes.py](reproduction_probes.py) and [results](reproduction_probes.json): figure orchestration, local data inventory, date counts, sharding.

From the repository root:

```sh
MPLCONFIGDIR=/tmp/codameter-review-mpl .pixi/envs/default/bin/python review/evidence/audit_probes.py
MPLCONFIGDIR=/tmp/codameter-review-mpl .pixi/envs/default/bin/python review/evidence/downstream_probes.py
MPLCONFIGDIR=/tmp/codameter-review-mpl .pixi/envs/test/bin/python review/evidence/reproduction_probes.py
```

These probes use existing local environments. They are diagnostics, not a new calibrated benchmark. The sparse-scoring probe supplies freshly generated arrays to the actual scorer. No private truth or external evaluation is used.

## Tests and document build

- [Targeted test log](pytest_targeted.log), [JUnit results](pytest_targeted.xml), [execution metadata](pytest_targeted_metadata.json).
- [Full-suite log](pytest.log) and [execution metadata](pytest_metadata.json): 540-second timeout. Partial progress: 261 passed, one skipped, 39 unfinished. No completed full-suite verdict.
- [Initial build log](paper_build.log): LuaTeX cache-permission failure.
- [Successful build log](paper_build_cached.log), [execution metadata](paper_build_cached_metadata.json).
- Fresh compiled manuscript: `reproduction_workspace/paper/manuscript_marine.pdf`.
- Visual QA: `figures/page_*.png` and `figures/fresh_page_*.png`.

The fresh PDF uses current source and pre-existing numerical graphics. Successful compilation does not establish experiment reproduction.

Reports, probe outputs, logs, and page renders are versioned.
The duplicate compilation workspace and font caches stay local.
They are excluded by `review/.gitignore`.
The fresh PDF path above describes a local audit artifact.
