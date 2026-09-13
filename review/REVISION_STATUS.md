# Revision reconciliation and remaining work

The principal formula and sparse-scoring defects have been repaired.
The paper is still not ready for submission. Full covariance validation,
deterministic comparison semantics, field provenance, and author end matter
remain incomplete.

This is a bounded evidence reconciliation, dated 2026-09-10. It checks the
revision commits through `62b63b5` and the subsequent Codex corrections in this
working tree against the 37 original findings. It is not a second full review
under the nine-scope reviewer workflow. The original reports and manifests
remain unchanged; their `OPEN` states are historical review states.

## Changes completed in this pass

- Added `golden.advisory_case` for all six applications. It uses public seasonal
  templates independently of installed evaluation recipes. Documentation uses
  per-channel recovery, fixed scoring support, and explicit availability.
- Removed claims that synthetic advice proves field performance, that one RMS
  comparison establishes equivalence, or that elicited site metadata is
  automatically simulated. Explained the three public cases, 30 templates,
  and limits of hidden recipes and the observables-only API.
- Rejected irregular/non-daily CCF rows before day-based stacking. Preserved
  irregular-time support for already measured inputs to `gibbs_dvv`.
  Applied coherence gating to moving-reference and non-stretching ensemble
  members, beyond the legacy pipeline's fixed-reference gate.
- Excluded unavailable member epochs and unusable coherence floors from
  conditional coverage; reported the observed count and missing fraction.
  All 600 archived locked realizations report zero missing fraction, so their
  published coverage values are unaffected.
- Included the use-case geometry source in golden cache identity.
- Corrected the manuscript and model documentation: joint hierarchical fitting
  is not discrete pipeline-mixture marginalization; member coverage does not
  validate the combined estimate, temporal covariance, or cross-band input.
- Enlarged the calibration table by transposing scenarios into columns;
  corrected abstract percent formatting and shortened the clipped running title.
- Removed unsupported statements that field products are already archived,
  the originating run commit is pinned, and author adjudication is complete.
  Small nonzero calibration standard errors are no longer printed as zero.
  The prior-rate diagnostic is distinguished from total prior influence.

## Scientific interpretation of the locked calibration

| Scenario | Realizations | Member 68% | Member 95% | Combined-estimate 95% |
|---|---:|---:|---:|---:|
| Clean | 200 | 0.808 | 0.956 | 0.590 |
| Shared source | 200 | 0.795 | 0.950 | 0.340 |
| Clock drift | 200 | 0.804 | 0.954 | 0.604 |

Source: `paper/data/calibration/locked_*.json`. Standard errors across independent
noise realizations are retained in those records and the manuscript table.
These are repeated realizations of specified scenarios, not validation across
independent field sites or waveform-physics families. The source coda is fixed
within the experiment; random seeds change daily noise and decorrelation.

The 95% member intervals pass the stated pointwise margin. The 68% member
intervals fail it. The combined estimate's credible band undercovers strongly.
Pointwise coverage contains no direct test of off-diagonal covariance. No
multi-chain convergence evidence or calibrated downstream interval follows
from these results. The revised text now keeps these distinctions explicit.

## Finding-by-finding reconciliation

“Verified” means the stated defect has direct local code or text evidence.
“Narrowed” means the unsupported claim was limited or withdrawn; it does not
mean the unperformed experiment succeeded. “Partial” retains outstanding work.
These assessments do not overwrite formal reviewer-ledger verdicts.

| Finding | Assessment | Evidence and remaining limitation |
|---|---|---|
| UQ-01 | Verified formula repair | `uq_measurement.py`; Eq. 21, unit-rescaling and bandwidth tests. Gaussian bandwidth convention remains an assumption. |
| UQ-02 | Verified variance repair | `uq_processing.py`; zero-mean mixture test; bias, SD and RMSE separated. |
| UQ-03 | Partial | Independence and joint-fit versus mixture distinction now explicit in manuscript and module. A dependence-aware likelihood is not implemented. |
| UQ-04 | Partial | Excess-spread subtraction and shared-artifact test exist. Temporal covariance and common-error scale remain unvalidated; 95% coverage alone is not closure. |
| UQ-05 | Verified for supported inputs | Daily-grid rejection, output-only decimation, moving-reference gate and missing-member tests. Inversion references explicitly rejected by the ensemble. |
| DET-01 | Partial | Estimand table names raw RMS and support. Canonical inversion still ignores requested estimator/stack; gates and valid supports vary across deterministic comparisons. |
| DET-02 | Verified cache repair | Exact cold/warm arrays and generator identity tests, now including use-case geometry. |
| INV-01 | Narrowed | Depth remains a framework. Manuscript distinguishes temporal from cross-band covariance and the member from combined-estimate target. GLS propagation remains unimplemented. |
| INV-02 | Verified defect repair | Nonzero local covariance and active-bound flags; disconnected epochs flagged. Local Gaussian curvature at a bound is not a bounded posterior interval. |
| SCALE-01 | Partial | Banded sampler update agrees with dense reference. Stored posterior and output covariance remain dense; no cloud-scaling study is claimed. |
| SCALE-02 | Verified shard checks | Missing/duplicate shard rejection and explicit partial manifest tests. No large deployment was executed here. |
| AG-01 | Verified advisor route repair | All six public development scenarios execute through `recover`; no dependence on missing mappings or hard groundwater fallback. |
| AG-02 | Narrowed | Six executable axes distinguished from contextual site metadata; single-seed equivalence rule removed. No site-conditioned agent evaluation supplied. |
| AG-03 | Narrowed | Synthetic support described as conditional; separated bands do not validate physical depth resolution. |
| EV-01 | Verified original exploit repair | Fixed support and baseline; ten-zero-plus-null regression. Null replacement can still improve a poor prediction; availability must accompany scores. |
| EV-02 | Deferred, explicit | Truth-key removal is not isolation. Private files, generator access and scorer metadata still require an isolated evaluation harness. |
| EV-03 | Deferred, explicit | Three public cases versus 30 templates documented; shared families and regression-derived thresholds remain. |
| EV-04 | Narrowed | Completed agent evaluation no longer claimed. No model transcripts or performance estimates added. |
| SCI-01 | Improved text | Estimand table separates pair spread, finite-network mean precision and posterior uncertainty. No new network covariance calibration. |
| SCI-02 | Narrowed | Scenario-conditional sensitivity and surrogate depth interpretation stated. Broad observational dominance remains unsupported. |
| SCI-03 | Narrowed | Raw trailing references described as an ablation. They still do not represent accumulated changes on a common datum. |
| SCI-04 | Partial | Estimator prescriptions qualified in prior revision. This pass does not repeat the independent literature assessment. |
| SCI-05 | Partial | 600 locked realizations, width/bias/failures and coverage records; missing-data metric repaired. Multi-chain diagnostics and broader calibration remain. |
| SCI-06 | Narrowed | Depth evaluation, agent performance and generalized cloud scalability withdrawn from demonstrated results. |
| SCI-07 | Partial | In-repo product comparison and explicit masks replace inconsistent counts. Original run provenance and raw-waveform replay still missing. |
| SCI-08 | Partial | Abstract-only nonreporting caveat corrected. Study-key deduplication and survey denominators still need reconciliation. |
| SCI-09 | Improved text | Branch rule predefined; same-data coherence-selection bias acknowledged. No new independent selection experiment. |
| SCI-10 | Verified text repair | Appendix WCC delay sign corrected against the defined dilation convention. |
| SCI-11 | Verified text repair | Signed, scenario-dependent stacking recovery replaces universal underestimation. |
| FIG-01 | Verified caption repair | WCS failure acknowledged against saved traces in the methods figure. |
| FIG-02 | Partial | Field masks and labels reconciled in captions/table. External figures retain historical annotations and uncorrected error bars, explicitly disclosed. |
| FIG-03 | Partial | Units, legend placement and sidecars improved. External field bars require regeneration; not all figure pages re-reviewed in this pass. |
| FMT-01 | Partial | Single-paragraph abstract and estimand table added. Author placeholders and full presentation review remain. |
| REP-01 | Partial | All synthetic generators registered with numerical sidecars. Three external field figures remain outside the executable build. |
| REP-02 | Partial, author input | Comparison code and correction log exist. Exact originating run, redistribution rights and archived field inputs remain missing. |
| REP-03 | Partial | Figure sidecars and locked settings improve replay. Release metadata, dirty-source/input hashes and a complete reconstruction manifest remain incomplete. |
| COMP-01 | Partial, author input | Availability and AI disclosure now describe actual state. Funding, contributions, archive details and final adjudication remain to be supplied. |

## Next revision tasks

1. **DET-01: make deterministic comparisons executable on a common target.**
   Reject unsupported inversion estimator/stack settings or implement them;
   apply a stated gate consistently; report raw and fixed-datum RMS on fixed
   support with availability. Regenerate affected OAT/factorial figures only
   after locking this specification. Preserve original metrics for comparison.
2. **SCI-05/UQ-03/04: validate the object actually used downstream.**
   Choose a single member, a mixture, or a combined estimator explicitly.
   Test covariance with contrasts and whitened errors, not only pointwise
   intervals; include shared artifacts and independent-chain diagnostics.
   Keep the current limited claims until this evidence exists.
3. **REP-02/FIG-02: complete field reproduction.** Obtain the original Gate 1
   commit and run configuration, archive the permitted inputs with hashes,
   and regenerate the three field figures using corrected uncertainty columns.
4. **SCI-08/REP-03/COMP-01: finish submission metadata.** Reconcile unique study
   counts; synchronize release/citation metadata; complete funding,
   contributions, data rights, archive identifier and human adjudication.
5. Run the complete reviewer reconciliation workflow after these changes.
   Preserve the iteration-1 manifest; update the live ledger from evidence.

## Verification

Exact test and build outputs are saved under `evidence/revision2/`.
Final suite: **342 passed, 1 skipped**, with no failures or errors. All configured pre-commit hooks passed. The manuscript rebuilt to **82 pages** with no unresolved-reference markers; pages 1, 2, 33, 37 and 62 were visually checked.
The first focused pass completed with 32 passing tests. Detailed versions and
source hashes are in `evidence/revision2/verification.json`.
No private corpus, external model, cloud deployment, or raw field waveform
reproduction was executed in this pass. Existing locked calibration records
and historical audit evidence were preserved.
