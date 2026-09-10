# Audit of the revision plan

Author: Fable (Claude), for Marine Denolle.
Date: 2026-09-10.
Audited: `review/REVISION_PLAN.md` and the iteration-1 review at `bc47511`.
Manuscript hash at audit: `sha256:582a09ee...` (unchanged since the review).

## Bottom line

The review's fatal findings hold. I re-derived UQ-01 against Weaver et al. (2011) eq. 20 and UQ-02 and EV-01 against the source, and re-read the code behind UQ-03/04/05 and INV-02. Nothing I checked is wrong. One tier is overstated (UQ-02), and the numerical reach of UQ-01 into the paper is smaller than the plan assumes.

The plan's working rules are good. Its shape is not. It schedules the expensive "supply the missing evidence" branch for the depth, advisor and cloud-scaling claims and only allows "narrow the claim" in the last package, although the review offered both branches for each. It puts the two one-file fatal fixes third, behind a specification package, when they are independent of it and everything downstream must be regenerated from them. And it never inventories which figures each fatal finding touches, so it cannot size the regeneration.

Decide the three scope questions now. If the answer is to narrow, the four packages that need external inputs or new experiments (R5 in part, R8, R9, the depth items of R6) shrink to code hygiene and the rest is a revision measured in weeks.

## What I verified

| ID | How | Verdict | Reach into the paper |
|---|---|---|---|
| UQ-01 | Weaver eq. 20, arXiv 1103.1785 p. 7; `uq_measurement.py:76-124` | Holds. Code omits T and its variance prefactor is (1-X^2)/(2X^2) against Weaver's (1-X^2)/(4X^2). Manuscript line 1340 already writes the correct 1/sqrt(B) dependence, so the paper is right and the code disagrees with it. | `demo_12_bayes` (ensemble bands 0.4-1.0 and 0.6-1.4 Hz, so member weights shift about 15%; the 2x prefactor is absorbed by the fitted s^2), the N_eff statement, and the field `dvv_err_within` column (constant factor at 2-4 Hz). Recovery-RMS figures, the sqrt(N) figure and the field r values do not depend on it. |
| UQ-02 | `uq_processing.py:220-266` | Holds; the code comment admits the proxy. | None. `per_band_marginal_error` has no caller outside tests and the depth section has no figure. Tier should be Major (code), not Fatal (paper). Five-line fix. |
| EV-01 | `frugalmind.py:299-307`, `golden.py:578-596` | Holds. Ten zeros land on pre-event days, the baseline is drawn from them, RMS is zero. | Advisor evaluation claim only. Existing test `test_series_scorer_truth_vs_null` does not cover it. |
| UQ-03/04 | `uq_bayes.py:297-344` | Holds. `method_std` is the raw across-member SD, which already contains within-method noise, then `within_std` is added again. Docstring at lines 37-39 contradicts the dataclass at 175-186. | `demo_12_bayes` diagonal and the "covers the truth at the nominal rate" sentence at line 1010. |
| UQ-05 | `uq_bayes.py:121-157` | Holds. `reference` and `gate` keys are ignored; CCFs are subsampled by cadence before stacking; cc is clipped to 0.5. | `demo_12_bayes`. |
| INV-02 | `linear_fit.py:544-549`, `uq_measurement.py:419-429` | Holds. Covariance zeroed at active bounds; pseudoinverse without a connectivity check. | No figure. Code hygiene. |
| SCI-10 | Manuscript lines 95-125 and 1349-1351 | Holds. With eps > 0 meaning a delayed phase, argmax of the integral of c(t) r(t - tau) sits at tau = +eps t_i, not -eps t_i. One-line fix. | Appendix text. |
| SCI-07 | `reproduction_probes.json`, manuscript line 1139 | Holds, and I can say where 681 probably comes from: 727 rows minus 46 lost to a 45-day centred window. The sentence attributes the count to the 150-day burn-in comparison, which leaves 578. Confirm in R7. | Deployment section and Fig. realdata_1. |
| SCI-08 | Manuscript line 1422 | Holds, and it is a direction error. Abstract-only "n/r" cells can only flip to "reported", so the apparent under-reporting is an upper bound on true under-reporting. The text calls it a lower bound. One sentence. | Appendix survey. |

Not independently verified: SCI-02/03/04/05/09, the FIG and FMT items, AG-02/03, EV-02/03/04, REP-02/03, DET-01, SCALE-02, COMP-01. I read the passages behind SCI-01 and SCI-06 and agree with both; the fix for SCI-01 is textual (abstract, Table 2, section 3.3), not experimental, because lines 476-480 already state the SD-versus-SE distinction.

## Critique of the plan

**1. It defers the decision that sets its size.** The abstract promises depth propagation, robust advisor evaluation, and laptop-to-cloud scalability. The review gave each an "add the evidence" branch and a "narrow the claim" branch. The plan takes the first for all three and leaves narrowing to R10. That is backwards: the decision determines whether R5, R8 and R9 exist. My recommendation is to narrow all three. Keep the depth section as the framework it already says it is, and cut "illustrate its use by propagating errors" from the abstract. Describe the advisor and golden set as infrastructure and cut "robust evaluation". Replace "scalability from laptop to cloud" with the one workload that was run. Under that decision the closure modes are:

| Mode | Findings |
|---|---|
| Fix | UQ-01, UQ-02, UQ-05, DET-02, INV-02, EV-01, AG-01 routes, SCI-01/03/07/08/09/10/11, FIG-01/02/03, FMT-01, REP-01/03, COMP-01, SCALE-02, the double-count and docstring parts of UQ-03/04, SCI-05 |
| Narrow | SCI-06, EV-04, AG-02/03, INV-01, SCALE-01, SCI-02 (conditional wording), SCI-04 (qualify prescriptions) |
| Defer as stated future work | EV-02, EV-03, the joint-likelihood question in UQ-03 |
| Needs Marine's input | REP-02 (external comparison driver) |

The reviewer skill has no "claim withdrawn" verdict, but a C4 finding is RESOLVED when the changed text no longer makes the claim. Each package should name the mode it intends per finding so iteration 2 checks the right thing.

**2. The order is wrong for the fatal math.** R3's two fixes are one file each, analytically testable, and independent of R1. Putting an eight-item specification package ahead of them delays the corrections that the Bayes figure, the field error bars and the calibration experiment all depend on. Run R3 and R2 as the first two pull requests, in parallel, and write the R1 specification alongside them.

**3. Inventory before derivation.** R3's last checkbox, "Inventory affected figures", should be its first. The table above is that inventory. The finding that s^2 absorbs the prefactor and that only the two-band ensemble and the error-bar scale change is what tells you the regeneration is one figure and two columns, not the paper.

**4. The field error bars do not need the external pipeline.** REP-02 is listed as an input the plan waits on. For UQ-01 it is not: the parquet files carry a per-epoch `cc` column, the band is fixed at 2-4 Hz and the window is known, so `dvv_err_within` can be recomputed from the corrected formula without rerunning correlations. The r values do not change. The external driver is still needed to regenerate the comparison statistics, but that is a separate finding.

**5. R4 breaks the plan's own splitting rule.** DET-02 (cache identity, atomic writes, dtype) is infrastructure. UQ-05 (stack durations under cadence, ignored reference axis) is science. The plan says to split such packages; R4 combines them.

**6. The acceptance criteria are mostly not testable.** "Every reported quantity has units, assumptions, and target" and "code and manuscript use the same definitions" cannot fail. R6 says to predefine margins and then does not. Proposals: R1 closes with a single estimand table in the manuscript (quantity, units, datum, evaluation support, target) that every figure caption cites. R3 closes when a test reproduces Weaver's own numeric example (eq. 21: t1 = 12.5 us, t2 = 50 us, omega_c = 15 rad/us, T = 0.56 us gives 4e-4 times sqrt(1-X^2)/(2X)) and a unit-rescaling test returns the same fraction. R6 margins: 95% pointwise coverage within 3 points of nominal at 200 or more independent realizations, bias below 10% of the event amplitude, width reported as a ratio to truth RMS, and failure rate reported alongside.

**7. R5 as written is a research program.** "Compare a dependence-aware joint model with a pipeline mixture", "represent shared waveform and reference errors explicitly", GLS in the stress inversion, and time-band covariance shapes are a second paper. The minimum this paper needs for its C_d claim is smaller: remove the double count (the between-configuration term should come from the beta_k spread or from member means with within-method noise subtracted, not from the raw member SD); fix the docstring; replace the single-realization "covers at the nominal rate" sentence with the R6 coverage number; and state the shared-artifact limitation, using the reviewer's four-identical-sinusoids counterexample as the stated limit of what agreement can detect.

**8. R9's banded solver is small; the scaling study is not.** The Gibbs precision matrix is a diagonal plus a pentadiagonal second-difference term. `scipy.linalg.solveh_banded` turns the cubic step into a linear one in a few dozen lines. Do that regardless. Do not run scaling experiments unless the claim stays.

**9. Items the plan lacks.**

- The reviewer skill reads its manifest from `reviews/<id>.review.json`. Astra wrote `review/codameter-gji.review.json`. Unless the file is moved, linked, or the skill is pointed at it, iteration 2 starts a fresh iteration 1 and the ledger is lost.
- The local skill is now v2.5 (commit `c6f09c9`, adds the scientific-register subagent); the review ran v2.4. Expect an INTRODUCED-BY-RECALIBRATION bucket. That is not a regression.
- No effort estimates or target date, so feasibility cannot be judged.
- The full suite does not finish in the 540 s budget. Add a slow marker so the pre-push check actually runs.
- REP-01: six figure generators are outside `paper/build.py`. "Regenerate derived artifacts" means nothing until they are wired in. That is week-one plumbing, not an R7 item after R6.

## What the plan gets right

Never refresh golden thresholds to pass. Preserve the review and its probes as regression evidence. Separate mathematical correctness from calibration. Pilot before expensive runs. Small commits. The inputs table. Keep all of that.

## Proposed first two weeks

Week one, in parallel:

1. Marine answers the three scope questions.
2. PR: Weaver floor takes a bandwidth argument, uses the eq. 20 prefactor, documents the T convention; tests for the eq. 21 anchor, unit invariance and bandwidth dependence; update the two callers; recompute the field `dvv_err_within` column from `cc`.
3. PR: `per_band_marginal_error` drops the floor-variance term, returns bias and RMSE as separately named fields.
4. PR: scorer evaluates on a support fixed by the task, treats missing values as failure or as an availability penalty, draws the baseline from truth-defined epochs; add Astra's ten-zero probe as a test.
5. PR: `paper/build.py` runs every figure generator and writes the numerical arrays beside each figure.
6. Move or link the manifest to `reviews/codameter-gji.review.json`.

Week two: UQ-05 (honor or reject `reference` and `gate`; stack before decimating), INV-02, the C_d double count and docstring, regenerate `demo_12_bayes`, then the R6 pilot for coverage on the Bayes synthetic.

Then one manuscript pass merging R1 and R10: estimand table, abstract, SCI-07 count, SCI-08 direction, SCI-10 sign, captions. Then iteration 2 of the reviewer.

## Readiness for iteration 2

The manuscript hash is unchanged since the review, so the iteration-2 diff will be exactly the revision. Name ledger IDs in every commit message so the reconciliation can cite changed text. Re-run `review/evidence/audit_probes.py` and `downstream_probes.py` as the closure evidence for the code findings; their JSON outputs are the before, the re-run is the after.
