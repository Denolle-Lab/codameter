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
- [x] **D. Figure build (REP-01).** `paper/build.py --figures` runs the deviations, multiverse and Bayes generators; every generator writes arrays and metadata beside its PNG. Real-data figures are documented as externally generated with their source run.
- [x] **E. Small fixes.** INV-02: no covariance zeroing at active bounds, flag `at_bound`; connectivity check in `global_reference_inversion` with NaN sigma for unidentified epochs. DET-02: cache key includes package version and generator source hash; one dtype on both routes; atomic writes. SCALE-02: aggregation rejects duplicate task ids and missing shards. SCALE-01: banded solve in `gibbs_dvv`; docstring says what `Cd` is.

## Phase 2: semantics and calibration

- [x] **F. Ensemble semantics (UQ-05).** Honor `reference` and `gate` or raise; stack in physical days before decimating; mask low coherence instead of clipping; time-aware second-difference prior or reject irregular grids.
- [x] **G. Measurement covariance (UQ-03/04).** Between-configuration variance with within-method variance removed; prior-sensitivity test; shared-artifact limitation stated with the four-sinusoids case.
- [x] **H. Calibration (SCI-05).** Driver, tests, 20-realisation pilots and locked 200-realisation runs done for clean, shared_source and clock_drift; the manuscript quotes the locked values. Script over independent realizations: 68/95 percent pointwise coverage, width, bias, failures, plus one shared-drift scenario. Pilot 20 seeds, then 200. Predefined margin: coverage within 3 points of nominal. Table replaces the single-realization sentence.

## Phase 3: manuscript pass (R1 + R10)

- [x] Estimand table cited by every caption (SCI-01); Table 2 split.
- [x] Single-paragraph abstract narrowed per the decisions (SCI-06, EV-04, FMT-01).
- [x] WCC/MWCS sign (SCI-10); signed recovery errors (SCI-11); predefined branch rule (SCI-09).
- [x] Trailing reference presented as an ablation (SCI-03); estimator prescriptions qualified against Yuan et al. 2021 (SCI-04); conditional wording for dominance and the surrogate (SCI-02).
- [x] LJR count from an explicit mask, NZ/NE label, statistics from one output (SCI-07, FIG-02); survey bound direction and extraction statuses (SCI-08).
- [x] Figure 1c trace vs caption, units, legends, full-range views (FIG-01, FIG-03).
- [~] Data availability and end matter (COMP-01, REP-02, REP-03): availability statement and AI disclosure drafted; funding, contributions, archive DOI and the noisepy-dvv-cloud commit need Marine.

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
- 2026-09-10: step E done (INV-02 bounds and connectivity, DET-02 exact versioned cache, SCALE-02 aggregation checks, SCALE-01 banded sampler). Step D code and tests are in; the full figure regeneration with sidecars is running and its outputs land in the next commit.
- 2026-09-10: steps F, G and the H driver done; all generated figures regenerated with sidecars. Bayes demo under the corrected ensemble: s 12.1, L 39 d, N_eff 22.8 of 229, no missing epochs (default prior has no gating). Three coverages of the truth on that realization: member level 0.955 at 95% and 0.80 at 68% (Cd as a per-measurement covariance is close to calibrated); credible band 0.64 (under-covers: shared bias mean(mu - truth) = -1.5e-4, RMS 7.5e-4); mu +- sigma_Cd 1.00 (over-wide by construction, this is the comparison the manuscript currently quotes and it must go). Prior shares: tau^2 a few percent, lambda up to ~10% for very smooth series (reported in prior_weight). demo_7_reference.png differs from the committed render with unchanged code: check in the Phase 3 figure pass. Pilot calibration (20 clean + 20 shared-drift) running.
- 2026-09-10, Phase 3 in progress. Pilot calibration, clean scenario, 20 realisations: member-level coverage 0.955 +- 0.001 at 95% (within the predefined 3-point margin) and 0.804 +- 0.003 at 68%; credible band on mu covers the truth 0.593 +- 0.011; mu +- sigma_Cd covers 1.000 (the comparison the draft quoted; dropped); s = 11.7 +- 0.1; tau^2 prior share 0.10 +- 0.03; N_eff 33 +- 2 of 229. Field comparison recomputed by scripts/compare_gate1.py under stated rules: LJR 0.985 on 579 d (slope 1.07), ARV 0.905 on 357 d (slope 2.15), RXH 0.829 on 446 d (slope 0.81); the draft's 681 days was the raw daily overlap. Figure 1c checked from its sidecar: WCS fails on the noisy landslide signal (3.8% RMS) and the caption now says so. Manuscript part 1 applied (abstract, introduction, estimand table, results wording, branches, stacking, deployment, discussion, conclusions, appendices, availability, AI disclosure draft); part 2 (Bayes section) waits for the shared-drift pilot. Legends moved off the data in seven figures; deviations panel retitled RMS.
- 2026-09-10, calibration scenarios. The clock-drift pilot (20 realisations) is indistinguishable from clean (member 95% coverage 0.953, credible band 0.61, no shared bias): a lapse-independent shift has opposite signs on the two branches and every default configuration measures both, so it cancels, as Section 3.9 says. The scenario is kept under its real name (clock_drift) as an immunity test, the manuscript sentences that asserted a shared drift bias were removed before any commit, and a genuine shared artefact (seasonal late-coda source noise beyond 6 s lapse, 0.2% spurious seasonal dv/v) is added as shared_source and piloted. Locked 200-realisation runs will use single-threaded BLAS; six workers with default threading drove the load average past 200.
- 2026-09-10: full test suite after Phases 1-3 code: 327 passed, 1 skipped (disba present), 19 min on a loaded machine. Closure re-runs of Astra's probes are under review/evidence/closure/.
- 2026-09-10: Phase 3 committed (b426c4e). Manuscript builds to 80 pages with no unresolved references. Locked calibration runs (200 realisations, seeds 2000-2199, single-threaded BLAS, 6 workers) started 12:54 for clean, shared_source, clock_drift in that order; when they land, regenerate calibration_table.tex, refresh the abstract and Bayes-section numbers, rebuild, commit. Phase 4 (reviewer iteration 2 against b6dbbd0) is ready to run.
- 2026-09-10: Gate 1 error columns rescaled to the corrected floor (scripts/correct_gate1_within_error.py; factor 0.328 at 2-4 Hz, originals kept, log in dvv2y/correction.json); the member windows were not needed because all members share the band. noisepy-dvv-cloud/src/noisepy_dvv_cloud/dvv.py switched to weaver_stretching_error_band (edited in that repository, left uncommitted for Marine). Still needed from Marine: the Gate 1 run commit and --use-case.
- 2026-09-10: locked runs done (200 realisations each, seeds 2000-2199, 56-58 min per scenario). Clean: member 95% 0.956 +- 0.000, 68% 0.808, credible band 0.590 +- 0.004, s 11.67. Shared source: member 95% 0.950, credible band 0.340, RMSE(mu) 0.161% vs 0.067%. Clock drift: member 95% 0.954, credible band 0.604 (immune, as stated). Table regenerated from the locked runs; manuscript numbers refreshed; PDF 80 pages, clean. Phase 4 is next and is Marine's call.
