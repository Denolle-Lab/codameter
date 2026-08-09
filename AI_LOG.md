# AI use log

A dated, append-only record of AI-assisted planning/work sessions on this
package and its paper (`paper/manuscript_marine.qmd`), in the spirit of the
group's "always log AI use" practice. This is a summary log, not a raw
transcript — one entry per session, capturing what was decided and why.

## 2026-08-08 — Scope stress correctly; add efficiency, real-data deployment, and agent/golden-dataset sections to the manuscript

**Tool**: Claude Code (Claude Sonnet 5).

**Prompted by**: codameter has been tested against a larger-scale deployment
(surfacing real computational bottlenecks, now fixed) and a real-data
companion pipeline (`noisepy-dvv-cloud`, correlating CI.LJR via NoisePy on AWS
Batch Fargate Spot) is now running. The manuscript needed to catch up, and
the existing `§sec:stress` section needed a scope correction.

**Decisions made** (all reviewed and approved by the author before any file
was edited):
- `§sec:stress` is *not* deleted, but its dv/v-to-stress conversion
  methodology (the acoustoelastic equation, its best-practice table, and the
  "companion framework, Denolle in prep." forward promise) is cut. The
  section is rewritten as an explicit scope statement: this paper stops at
  the depth-resolved velocity-change posterior and its covariance; it does
  not convert that to stress, and does not promise to. Motivating mentions
  of stress elsewhere (abstract, §bayes, §depth) are left as-is since they
  don't have this problem — they say the covariance is useful input to such
  work, not that this paper performs it.
- A new section, "Toward deployment: a real-data retrospective pipeline"
  (`§sec:deployment`), describes the `noisepy-dvv-cloud` architecture and its
  validation protocol against the published Clements & Denolle (2023) CI.LJR
  result. Written architecture-only at the time of this edit (the real
  pipeline was, per live recon, an early scaffold with zero results
  produced) — left an explicit placeholder for the dv/v(t) figure the author
  is producing separately, with an instruction not to describe results ahead
  of having them.
- A short paragraph on the recent vectorized-fast-path speedups was added to
  the end of `§sec:multiverse`. The cited numbers were independently
  re-measured in this session rather than trusted from the commit
  message/CHANGELOG, which turned out to be optimistic (measured ~2x/~3x/~3x
  across repeated runs vs. previously documented ~2.3x/~4.9x/~4x) —
  `CHANGELOG.md` was also corrected to match, since leaving it wrong would be
  inconsistent with this paper's own thesis about honest, verified
  reporting.
- The Introduction's one-sentence description of codameter's agentic/skill
  layer was reworded to match what `codameter.frugalmind`/`golden.py`/
  `private_golden.py` actually do (RMS-recovery scoring against seeded
  synthetic golden cases, including a hidden-truth variant), replacing an
  inaccurate "evaluation against base models" framing.
- Opportunistic fix: the Data Availability section referenced a stale
  manuscript filename (`paper/manuscript.qmd`, pre-dating the switch to
  `manuscript_marine.qmd` under `gji.cls`).

**What the author did, not delegated**: the CI.LJR real-data run itself (in
progress separately); the go/no-go on all of the above via an explicit
plan-review step before implementation.
