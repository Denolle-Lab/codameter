# Execution plan for Astra's iteration-1 findings

Owner: Fable (Claude), with Marine Denolle.
Approved: 2026-09-10 (Marine: "I like the plan, write it somewhere and execute it").
Supersedes the "Next implementation task" section of `REVISION_PLAN.md`; the package definitions there remain the reference for finding groupings.
Live ledger: `reviews/codameter-gji.review.json`. Audit: `PLAN_AUDIT.md`.

## Decisions taken (defaults, approved with the plan)

1. Depth propagation stays a framework section; the abstract no longer claims a demonstrated propagation. Closes SCI-06 (depth), INV-01 by changed text.
2. Advisor and golden set are described as infrastructure; "robust evaluation" is dropped from the abstract. Closes EV-04, AG-02, AG-03 by changed text. EV-02 and EV-03 are stated as future work.
3. Laptop-to-cloud scalability is replaced by the one workload that ran. Closes the claim half of SCALE-01.
4. The Clements and Denolle comparison script in noisepy-dvv-cloud is an external dependency, pinned by commit in the data README (REP-02, needs the commit from Marine).

Consequence: `REVISION_PLAN.md` packages R8 and R9 reduce to the code items listed under Phase 1.

## Phase 1: correctness (independent steps, one commit each)

- [x] **A. Weaver floor (UQ-01).** Required `bandwidth_hz` argument; eq. 20 prefactor; T = sqrt(ln 10)/(pi B), matching band edges to Weaver's -10 dB points; core function taking T directly. Tests: eq. 21 anchor, unit-rescaling invariance, bandwidth monotonicity, existing monotonicity. Update `uq_bayes` and `uq_processing` callers. Regenerate `demo_12_bayes.png`. CHANGELOG entry.
- [x] **B. Mixture variance (UQ-02).** `per_band_marginal_error` returns within, processing (zero unless conditional means are supplied), bias, sd and rmse as separate fields. Test against the probe value 1.79521e-6.
- [x] **C. Scorer (EV-01).** Gold record carries a fixed support (epochs where the reference pipeline is valid) and fixed baseline epochs; missing values inside the support count as error; scorer spec versioned; availability rule shared with the parameter scorer. Tests: ten zeros plus nulls scores 0; truth on support scores 1; sparse constants score low.
- [ ] **D. Figure build (REP-01).** `paper/build.py --figures` runs the deviations, multiverse and Bayes generators; every generator writes arrays and metadata beside its PNG. Real-data figures are documented as externally generated with their source run.
- [ ] **E. Small fixes.** INV-02: no covariance zeroing at active bounds, flag `at_bound`; connectivity check in `global_reference_inversion` with NaN sigma for unidentified epochs. DET-02: cache key includes package version and generator source hash; one dtype on both routes; atomic writes. SCALE-02: aggregation rejects duplicate task ids and missing shards. SCALE-01: banded solve in `gibbs_dvv`; docstring says what `Cd` is.

## Phase 2: semantics and calibration

- [ ] **F. Ensemble semantics (UQ-05).** Honor `reference` and `gate` or raise; stack in physical days before decimating; mask low coherence instead of clipping; time-aware second-difference prior or reject irregular grids.
- [ ] **G. Measurement covariance (UQ-03/04).** Between-configuration variance with within-method variance removed; prior-sensitivity test; shared-artifact limitation stated with the four-sinusoids case.
- [ ] **H. Calibration (SCI-05).** Script over independent realizations: 68/95 percent pointwise coverage, width, bias, failures, plus one shared-drift scenario. Pilot 20 seeds, then 200. Predefined margin: coverage within 3 points of nominal. Table replaces the single-realization sentence.

## Phase 3: manuscript pass (R1 + R10)

- [ ] Estimand table cited by every caption (SCI-01); Table 2 split.
- [ ] Single-paragraph abstract narrowed per the decisions (SCI-06, EV-04, FMT-01).
- [ ] WCC/MWCS sign (SCI-10); signed recovery errors (SCI-11); predefined branch rule (SCI-09).
- [ ] Trailing reference presented as an ablation (SCI-03); estimator prescriptions qualified against Yuan et al. 2021 (SCI-04); conditional wording for dominance and the surrogate (SCI-02).
- [ ] LJR count from an explicit mask, NZ/NE label, statistics from one output (SCI-07, FIG-02); survey bound direction and extraction statuses (SCI-08).
- [ ] Figure 1c trace vs caption, units, legends, full-range views (FIG-01, FIG-03).
- [ ] Data availability and end matter (COMP-01, REP-02, REP-03).

## Phase 4

- [ ] Diff against `b6dbbd0`; run the reviewer in reconciliation mode; reconcile the ledger.

## Inputs needed from Marine

| Input | Blocks |
|---|---|
| Gate 1 member configurations (windows per member) or the run manifest | Recomputing field `dvv_err_within` from `cc` |
| noisepy-dvv-cloud commit for `scripts/compare_cd2022.py` and the real-data figure scripts | REP-02, SCI-07 recomputation, real-data figure provenance |
| Archive destination and rights for the field products | Data availability |
| Authorship, funding, contributions | End matter |

## Log

- 2026-09-10: plan written; Phase 1 started on branch `docs/sign-convention-manuscript`.
- 2026-09-10: step A done. Bayes demo before/after the corrected floor: s 6.16 -> 10.35, tau 3.85e-4 -> 3.72e-4, L 21.2 -> 21.3 d, N_eff 18.0 -> 18.6 of 229, median calibrated within-method sigma 1.87e-3 -> 1.89e-3 (s absorbs the constant, as predicted). Raw floor medians now 2.7e-4 (0.4-1.0 Hz) and 1.8e-4 (0.6-1.4 Hz). The Cd +-1.96 sigma band covers 100% of truth epochs before and after, the posterior band 49-50%: the "nominal rate" sentence in the Bayes section is wrong in the over-wide direction (Phase 2, step G). s of 10 means the residual scatter is an order of magnitude above the coherence floor; report it in Phase 3.
- 2026-09-10: step B done. No figure or manuscript number depended on the function.
- 2026-09-10: step C done. Ten zeros plus nulls now score exactly as all zeros on the public cases; manifest expected metrics unchanged. Found on the way: the cached float32 CCFs shift the oracle RMS by 2.4e-8 relative (DET-02, step E), and the mypy hook env had drifted to numpy 2.5 (pinned).
