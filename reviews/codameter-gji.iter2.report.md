DENOLLE GROUP PRE-SUBMISSION REVIEW
=====================================
Manuscript: The reproducibility cost of ad-hoc processing choices in ambient-noise seismic velocity-change monitoring   Target: GJI, research paper with methods emphasis   Date: 2026-09-10
Reviewer: Pre-Submission Orchestrator (10 subagents -> 8-criterion synthesis)
Note: Advisory. All findings require human judgment before submission.
Profile: default
Provenance: Skill v2.5 (commit 211bcc1) | Model claude-fable-5-1 | Iteration 2 | Manuscript hash 6b4b9eb91fb2 | Repository c10a108
Mode: Reconciliation, delta vs. iteration 1 (v2.4, Codex/GPT-6, commit b6dbbd0)
Conflict note: The iteration-2 orchestrator (claude-fable-5-1) is the agent lineage that drafted most of the revision; the ten subagents ran as independent contexts and their stricter verdicts govern. A parallel Codex session committed three further revision commits (af35b27, 359727a, c10a108) before this run; those changes were reviewed as part of the current text.

SUMMARY
The paper quantifies how processing choices move ambient-noise dv/v and its stated uncertainty on truth-known synthetics, and now backs its measurement covariance with a 200-realisation calibration per scenario, a reproducible field comparison, per-figure numerical sidecars and a corrected Weaver floor. Both iteration-1 Fatal uncertainty defects and the scorer exploit are fixed in code and verified by independent probe re-runs and a bit-identical replay. Claims are now bounded to what is shown: depth propagation is an interface, the advisor is infrastructure, and the credible band on the ensemble mean is reported as under-covering. The revision also introduced defects of its own, two of them Poor (the Appendix A sign statements for four estimators; an unreadable figure panel) and several Fair (a false survey denominator with a mis-citation, twelve undisclosed empty multiverse pipelines, a misread step-error sign, an unimplemented branch rule, comma artefacts in headline numbers, provenance gaps). Readiness improves from Major revision required to Revise before submission; the archive, field provenance and end matter remain hard gates.

SUBMISSION READINESS
  [ ] Ready  [x] Revise before submission  [ ] Major revision required  [ ] Not ready
  Delta vs iteration 1: Major revision required -> Revise before submission. 13 RESOLVED, 24 PARTIALLY ADDRESSED, 0 NOT ADDRESSED, 0 REGRESSED; 24 introduced-in-revision entries (2 Poor, 15 Fair, 7 grouped minor); 1 recalibration bucket (S-PR).
  FATAL: none
  MAJOR (Poor, introduced): S-ME.N1 Appendix A estimator sign statements | S-FD.1 Fig 8 panel (d) unreadable
  MAJOR (Fair, prior, still open): UQ-03/UQ-04 (working likelihood; R and tau^2 term unvalidated) | DET-01 (comparison semantics) | UQ-05 (factorial stacks in 3-day records) | SCI-05 (in-sample coverage, no convergence diagnostic) | SCI-06/INV-01 (depth section sentences 1232-1234, 1251-1253) | SCI-07/FIG-02 (Fig 15 text vs plot) | SCI-08 (survey denominator) | REP-02 (field provenance, BLOCKING reproduction stop) | REP-03 (release metadata) | COMP-01 (end matter)

STRENGTHS
- Weaver floor now matches eq. 20 of Weaver et al. (2011) and reproduces their eq. 21 example; the fitted rescale s ~ 12 is reported rather than hidden (S-ME, S-RP).
- Cd is calibrated as a single-member covariance on 600 locked realisations with a margin fixed before the runs; the credible band's under-coverage and the shared-source limit are stated (S-ME, S-RE, S-CO).
- Every quoted number with a source reproduces: Fig 1 RMS values from the sidecar, Table 6 from the comparison script byte-for-byte, the calibration table from the locked JSON (S-RE, S-RP).
- Scope is consistent across abstract, introduction, discussion and conclusions (S-AB, S-IN, S-CO).
- The scorer exploit is closed and tested; the cache is exact and versioned; shard aggregation refuses incomplete input (S-RP).

RESPONSE-CHECK DELTA (prior findings)
ID | iter-1 tier | verdict | evidence
UQ-01 | Fatal | RESOLVED | S-ME: uq_measurement.py:80-147 implements Weaver eq. 20 with T; Appendix eq:weaver 1585-1591; eq. 21 anchor, unit invariance and 1/sqrt(B) tests pass.
UQ-02 | Fatal | RESOLVED | S-ME: uq_processing.py:253-328, zero-mean mixture test; feeds no manuscript number.
UQ-03 | Poor | PARTIALLY ADDRESSED | S-ME: working-likelihood caveat 1073-1077 and measured consequence (posterior 0.59); code still sums precisions (uq_bayes.py:425-426); no joint likelihood, no duplicate-pipeline test; prior share 0.09 reported.
UQ-04 | Poor | PARTIALLY ADDRESSED | S-ME: double count removed (uq_bayes.py:488 = eq:cd); docstrings fixed; shared-error limit tested and quantified (0.34 posterior coverage); R and tau^2 11^T unvalidated, no derivation from a stated error model (text says so, 1114-1120).
UQ-05 | Fair | PARTIALLY ADDRESSED | S-ME: Bayesian ensemble fixed (uq_bayes.py:96-186, tests); S-RP: deviations.multiverse still decimates CCFs before stacking (deviations.py:345-346), so the 108-pipeline factorial's 10-day stack spans 28 days and text 924/936 does not say so; REPRODUCTION-STOP R5.
DET-01 | Fair | PARTIALLY ADDRESSED | S-ME: datum and support stated (363-366, Table 2) but code unchanged: gated fixed baseline vs ungated moving/inversion on the reference axis; inversion ignores estimator; single seed; not closable by narrowing.
DET-02 | Fair | RESOLVED | S-RP: golden.generate 555-605 float64, atomic write, key = recipe + generator hash (version + source of golden, synthetic_demo, use_cases); probe float64/float64 array_equal True; two tests.
INV-01 | Poor | PARTIALLY ADDRESSED | S-ME/S-DI: narrowed at 1118-1120, 1227-1228, 171-173; but 1233-1234 still says C_m inherits C_d's temporal structure and uq_measurement.py:33-35 still says the full C_d closes the loop; no GLS path.
INV-02 | Poor | RESOLVED | S-ME: linear_fit.py:528-575 at_bound; uq_measurement.py:536-554 components; tests pass; residual: summary() symmetric intervals can cross the bound.
SCALE-01 | Fair | PARTIALLY ADDRESSED | S-RP: banded mu-update (uq_bayes.py:404-441, equivalence test); no scaling claim remains in the text (1095-1096); mu_cov, Cd and samples stay dense O(T^2); no runtime/memory scaling reported.
SCALE-02 | Fair | RESOLVED | S-RP: bench.check_shards 332-379 and _cmd_aggregate 422-442 refuse missing shards, duplicate cells, mixed versions; aggregate_manifest.json; test passed.
AG-01 | Fair | RESOLVED | S-RP: golden.advisory_case 507-526 for every application; tests/test_advisor_validation.py parametrised over all use cases; validation_loop.md routes through it. Residual: MAINSTREAM_BY_USE_CASE still has three keys (public trap).
AG-02 | Fair | RESOLVED | S-RP: validation_loop.md 49-60 removes the 20% equivalence rule and separates executable axes from context; manuscript 184-185. Residual: recommend() validates keys not values.
AG-03 | Fair | RESOLVED | S-DI: SKILL.md 'assesses conditionally'; no advisor claim in the paper; S-RP to confirm.
EV-01 | Fatal | RESOLVED | S-RP: inline probe sparse 0.0 / truth 1.0; _gold fixes support and baseline (frugalmind.py:179-203, golden.py:651-701); SCORER_CONFIG v2; tests passed. Residual: availability computed but discarded.
EV-02 | Fair | PARTIALLY ADDRESSED | S-RP: documented, not implemented: truth keys stripped in-process (golden.py:608-624); rows export recommended_config (frugalmind.py:242-244); manuscript claims only a hidden-truth variant (183-184).
EV-03 | Fair | PARTIALLY ADDRESSED | S-RP: counts reconciled (golden_datasets.md 3-7); thresholds still manifest-derived; families shared; not claimed as a result in the paper.
EV-04 | Poor | RESOLVED | S-AB: claim withdrawn (abstract 47-48, intro 184-185); S-RP to confirm no residual claim in code docs.
SCI-01 | Poor | PARTIALLY ADDRESSED | S-RE/S-FD: estimands defined (Table 2, 517-534), mixed row deleted; pair covariance named not computed; Table 2 datum wrong for Section 3 (S-RE.1/S-FD.3/S-ME.N2); Fig 3 caption unchanged. Tier Poor -> Fair.
SCI-02 | Fair | PARTIALLY ADDRESSED | S-DI/S-ME: dominance conditioned (1419-1427); realisations redraw noise on one fixed coda and the text does not say so (S-DI.R2); framework 191/209 and 228-229 unchanged.
SCI-03 | Fair | PARTIALLY ADDRESSED | S-RE: ablation wording in Table 4 (1030-1032) and 941-945; Table 3 row 395-396, 'Scale of effect' 704-707 and the Fig 12 bar label still price 'moving'; no cumulated/stitched benchmark.
SCI-04 | Fair | PARTIALLY ADDRESSED | S-IN/S-RE/S-DI/S-CD: novelty delimited (143-146) and Results conditional (345-348); Table 4 line 1017 still cites Yuan2021 for 'robust at low SNR'; Yuan regime unstated; no tuned comparison.
SCI-05 | Poor | PARTIALLY ADDRESSED | S-ME/S-RE: 200 realisations, prefixed margin, values verified against locked JSONs; coverage is in-sample (calibration.py:150-171), single chain with no convergence diagnostic and settings unstated, one truth class; 68% fails margin (stated). Tier Poor -> Fair.
SCI-06 | Poor | PARTIALLY ADDRESSED | S-AB/S-IN/S-CO: abstract, intro, Discussion, Conclusions consistent (described, not evaluated); S-DI: depth 1251-1253 still promises a density-field 'documented extension (Section discussion)' that does not exist and 1232-1234 reads as delivered; one sentence from RESOLVED.
SCI-07 | Poor | PARTIALLY ADDRESSED | S-RP: compare_gate1.py reproduces comparison.json byte-identically; Table 6 and text match. S-RE/S-FD: Fig 15 annotations (0.86/0.58/0.37) do not match the caption (0.87/0.37/0.62), bars 3.1x too large, 1299-1300 'near 0.7' conflicts with Table 6, RXH attribution without metadata. Tier Poor -> Fair.
SCI-08 | Fair | PARTIALLY ADDRESSED | S-IN/S-CD: bound direction and groundwater attribution corrected; denominator now mis-stated (S-CD.1: two Obermann 2013 papers collide on one key; Piton row mis-cited); verified rate never reported; no search rules.
SCI-09 | Fair | PARTIALLY ADDRESSED | S-RE: rule predefined (871-874) but not what the pipeline does (branch='both' fits one stretch; no branch term in C_d, S-RE.4); 865-866 'researcher's judgement' remains.
SCI-10 | Fair | RESOLVED | S-ME: delay convention 1607-1613 consistent with Introduction; WCC sign; Jacobian; regression test. The same revision introduced S-ME.N1 (Poor): DTW/WTDTW slope statement wrong and 'every estimator returns eps mapped exactly' false for four estimators.
SCI-11 | Good | PARTIALLY ADDRESSED | S-RE: contradiction removed, zero crossing confirmed by rerun; but the metric's sign is misread (negative = drop over-estimated; -5.4% at 1 day is extreme-value bias of a minimum), S-RE.3. Tier Good.
FIG-01 | Fair | RESOLVED | S-FD/S-RE: caption 441-444 and text 419-426 match demo_1_methods.npz; residual: panel (c) title still 'MWCS cycle-skips' only.
FIG-02 | Fair | PARTIALLY ADDRESSED | S-FD: Fig 16 NZ matches plot; Table 7 exact; Fig 15 annotation/title/error-bar statements contradict the plot; Fig 17 title vs panel counts.
FIG-03 | Fair | PARTIALLY ADDRESSED | S-FD: units and RMS labels fixed, legends moved on Figs 1, 2, 10a; Fig 13a band invisible, fraction/percent mixed, Fig 14a legend covers the band, Fig 16 no colourbar; Fig 8 regressed (S-FD.1).
FMT-01 | Good | PARTIALLY ADDRESSED | S-AB/S-FD/S-IN: one-paragraph abstract, 'Figure x' gone; Acknowledgements placeholder (1725), citation order unchanged, Fig 8 duplicates Figs 5-7, Table 6 never cited.
REP-01 | Poor | RESOLVED | S-RP: figures.py registry 18 generators + 3 declared external; build.py --figures; test ties every includegraphics to a generator or a declared source; demo_1/8/9 regenerated equal committed sidecars. Residual: sidecar git_commit lacks a dirty flag (S-RP.1).
REP-02 | Poor | PARTIALLY ADDRESSED | S-RP: in-repo driver verified; README documents rules and the error-column rescale; availability now honest (1714-1721). Products still untracked with no sha256, run commit one of three candidates, --use-case unknown, three figures not regenerated. BLOCKING reproduction stop R4. Tier Poor -> Fair.
REP-03 | Fair | PARTIALLY ADDRESSED | S-RP: calibration JSON and sidecars record commit, versions, seeds; seed-2000 replay exact. CITATION.cff still 0.1.0 with a JGR preferred citation; version not bumped for any fix (tag v0.4.0 predates them); no versions, hardware or invocation in the text.
COMP-01 | Fair | PARTIALLY ADDRESSED | Orchestrator C8: Data availability (1701-1721) now states what is and is not archived; AI-assistance disclosure present (1725-1732, names Codex and Claude); funding, contributions, archive DOI still placeholders; CITATION.cff version 0.1.0 vs package 0.4.0; disclosure must record this second iteration.

INTRODUCED-IN-REVISION (only on changed spans)
S-ME.N1 | C2 | Poor | Appendix A | Appendix A (1607-1632): DTW/WTDTW slope statement wrong (slope of l(i)/f_s vs lapse is 1/(1+eps)-1 = dv/v, code returns it as dv/v); MWCS/WCS phase sign under numpy's convention is -2 pi f dt and the slope is returned directly as dv/v; 'every estimator returns eps, mapped exactly' false for four estimators.
S-FD.1 | C5 | Poor | Fig 8 | Fig 8 panel (d) (demo_6_stacking) collapsed to a sliver after the legend/layout change; (a),(b) legends overprint the x labels; no panel letters.
S-FD.2 | C5 | Fair | qmd 414, 420-426, 520, 1140-1143, 1161, 1494-1495, 1557-1558 | Sixteen '\\,\\%' outside math render as a literal comma ('0.04,%', '95,%') in the headline Fig 1 RMS values and the calibration coverages.
S-FD.3 | C2 | Fair | Table 2, qmd 313-320 | Table 2 says every recovery RMS uses a fixed reference from the first 60% of the record; true only for Section 4 (deviations.py:182). Section 3 figures use the noise-free generating reference, a 0.8-yr stack, or the five named schemes, so those RMS values are best-case numbers. (Also S-RE.1, S-ME.N2.)
S-RE.2 | C4 | Fair | Fig 13, qmd 963-996; deviations.py:317-330, 475 | Twelve of the 108 multiverse pipelines (MWCS x 4-14 s window) return no epochs; the RMS range, per-day SD, Sobol indices and the panel's off-axis count are computed on 96 without saying so.
S-RE.3 | C4 | Fair | qmd 749-754; synthetic_demo.py:2343-2350 | The stacking step-error metric (minimum over 120 post-event epochs minus pre-event median) is negative when the drop is over-estimated, not under-estimated; the -5.4% value at 1 day is the extreme-value bias of a minimum over noisy epochs. Direction misread in both drafts.
S-RE.4 | C2 | Fair | qmd 871-876; synthetic_demo.py:344-351; uq_bayes.py:488-494 | The stated branch rule ('measure both branches ... carry the between-branch difference as a term of C_d') is not what the pipeline does: branch='both' fits one stretch over |t|, and C_d has no branch term.
S-RE.5 | C5 | Fair | Fig 15 caption 1355-1366 | Fig 15 caption asserts centred-rule annotations 0.87/0.37/0.62 but the plot prints 0.86/0.58/0.37 (0.58 matches no rule), the title still says 'smoothing-matched', and the caption describes error bars that are not in the legend and are 3.1x too large. (Also S-FD.4, S-FD.5.)
S-CD.1 | C6 | Fair | Appendix C 1677-1679; paper/build_survey.py | '103 rows for 102 publications, Obermann2013 contributing two rows' is false: the two rows are different papers (JGR 10.1002/2013JB010399 and GJI 10.1093/gji/ggt043) colliding on one key in build_survey.py; the Piton row is mis-cited and the JGR paper is missing from the reference list.
S-ME.N3 | C4 | Fair | qmd 1151 | 'A station clock drift leaves every statistic unchanged' is contradicted at the table's own precision (s 10.88 vs 11.67 +- 0.03; member 95% 0.9543 vs 0.9561 +- 0.0003). (Also S-RE.6.)
S-ME.N4 | C3 | Fair | qmd 1084-1094 | Hyperprior values (InvGamma(2, 1e-8) for tau^2 and s^2, Gamma(2, 1e-10) for lambda), chain settings (one chain, 1200 sweeps, 400 burn-in, thin 2) and the MIN_COHERENCE = 0.5 missingness rule are absent from the text.
S-AB.N1 | C4 | Fair | abstract 38-41 | 'reproduces a published dv/v product' overstates a shape agreement after matched smoothing with amplitude slopes 1.07, 2.15 and 0.81.
S-DI.R1 | C4 | Fair | qmd 1516-1517 | The pre-correction anticorrelations r = -0.69, -0.45, -0.40 are cited to the v0.4.0 release notes, which do not contain them; the numbers exist nowhere in the repository.
S-RP.1 | C3 | Fair | figures.py:66-79 | Figure sidecars record git HEAD without a dirty-tree flag or source digest; nine figures record commit 7bfdcef although built from a tree whose generator edits landed later.
S-RP.2 | C3 | Fair | qmd 1701-1721 | Data availability names no tag, commit or archive; the committed artifacts come from five unreleased commits and the only tag predates every fix.
S-RP.3 | C3 | Fair | qmd 1710-1712 | 'python -m codameter.calibration reproduces Table' is not the command that produced it (three scenarios, --n 200 --start-seed 2000, ~58 min each); settings live only in the JSON.
S-RP.4 | C3 | Fair | bench.py:202-216, 332-379 | Shard provenance is keyed on the unbumped version string, so pre- and post-fix shards merge silently.
S-AB.N2-N5 | C4/C5 | Good | abstract | Abstract: temporal C_d named as the depth input where a per-band covariance is meant; 'fixed scoring support' and 'null-change penalty' undefined in the body; 54-word list sentence; the two-orders-of-magnitude RMS spread absent from the abstract.
S-IN.11-12 | C5 | Good | Introduction | NoisePy uncited at first body use (178); 'advisor skill' undefined jargon (180).
S-CO.12-14 | C4/C7 | Good | Conclusions 1549-1561 | 'up to two orders of magnitude' understates the body; the 'remain unvalidated' sentence misdescribes cross-band (not constructed) and shared errors (demonstrably invisible); 'target' and 'member' unglossed.
S-DI.R2-R6 | C4/C7 | Good | Discussion, depth | Calibration realisations redraw noise on one fixed coda and the text does not say so ('first step' overstates); two-band ensemble vs one-estimand rule unstated; depth 1226-1233 self-contradiction on what C_m inherits; 'more than the measurement noise' has no comparator; 'archived' vs 'not yet deposited'.
S-FD.6-11 | C5 | Good | figures | Fig 17 caption member counts; Table 2 cites Table 5 before 3-4; Fig 10b and 13b legends cover data; Fig 14 caption vs legend labels and 'encloses the members'; Fig 12 bar label 'moving' vs text; interpretive caption text in Figs 12, 13, 14c, 16 and Table 5.
S-RE.7-9 | C5 | Good | Results | Fig 14 legend labels; stale numbers after regeneration (0.71 vs 0.741; ~93x vs 104x; Fig 1c title; L about 40 vs 30 d mean); Fig 12 caption omits that two deviations beat the baseline.
S-CD.2-3 | C6 | Good | Results 346-348; Appendix C 1696-1697 | Yuan et al. (2021) ranking cited without its regime (|dv/v| <= 0.5%, 0-30% noise); the 'verified reporting rate' is named but never reported (per-field counts available from the CSV).

INTRODUCED-BY-RECALIBRATION (skill v2.4 -> v2.5)
S-PR.1-40 | C5 | Good | Scientific-register candidates from the new v2.5 scan (40 hits: 8 in new text, 24 unchanged); author's call, never a tier change. Cluster of anthropomorphism in the new Bayes/Discussion text (1083, 1125, 1147, 1163, 1488). See reviews/iter2/block_S-PR.md for the 40 candidates with one word-swap each.

CRITERION VIEW (all criteria changed)
C1 Scientific question and novelty: Good (was Good). Contribution delimited against Yuan et al. 2021; the joint-choice accounting with a calibrated covariance is the atypical recombination (S-CD); residual: state the Yuan regime and align Table 4 line 1017.
C2 Methods and soundness: Fair (was Fatal). UQ-01, UQ-02, UQ-05 (Bayes side), INV-02 fixed and verified; UQ-03/04 are stated working assumptions with measured consequences; DET-01 and the factorial stack semantics unfixed; Appendix A now wrong for DTW/WTDTW and the exact-map claim (S-ME.N1); Table 2 datum wrong for Section 3; branch rule not implemented.
C3 Reproducibility: Fair (was Poor). Synthetic results regenerate with provenance sidecars (verified); REPRODUCTION VERDICT: NOT RECONSTRUCTABLE, one BLOCKING stop (field products, run commit, use case, figure scripts); no DOI or tag covers the revised code; CITATION.cff stale; sidecar commits lack a dirty flag; the calibration command in the text is not the producing command.
C4 Evidence and conclusions: Fair (was Poor). Abstract claims trace (12 of 13); 'reproduces a published product' overstates; twelve empty pipelines undisclosed; step-error direction misread; 'leaves every statistic unchanged' false at table precision; negative correlations cited to notes that lack them; depth section still promises a density-field extension.
C5 Presentation: Fair (was Fair). Units, RMS labels and most legends fixed; Fig 8 panel (d) unreadable (Poor); 16 comma artefacts in headline numbers; Fig 15/17 captions contradict their plots; citation order unchanged; register candidates from S-PR are the author's call.
C6 Literature integration: Fair (was Fair). Bound direction and groundwater attribution corrected; the survey denominator statement is false and mis-cites one paper (Obermann key collision); Table 4 still cites Yuan2021 for the opposite claim.
C7 Impact: Good (was Good). Limitations paragraph states the four required limits; significance claimed at the level shown.
C8 Ethics and compliance: Fair (was Fair). Availability statement honest; AI disclosure present (must record this second iteration); funding, contributions, archive DOI and data licence for SCEDC-derived products still missing.

DIVERSITY SIGNALS (surfaced, not scored)
Self-citation 7.0% (9 of 129). Years 1951-2026, median 2017. GJI, JGR and GRL supply 53-57%. Study-site geography of the 103 survey rows (string-matched, human-verify): USA 26, theory/lab 15, Japan 13, Switzerland 6, La Reunion 5; no South Asian, African or South American mainland study beyond Peru and South Africa, possibly a search-coverage effect. Identity axes disabled by profile.

JOURNAL-SPECIFIC NOTES (GJI)
Summary: one paragraph, 437 words, within the 500-word cap. Data and code: RAS policy expects an accessible archive; none is deposited and the daily field products are untracked. A tagged release with a DOI, an archive of the 2-4 Hz products with hashes and licence, and cited data sources (SCEDC, the CD2023 release) are required before submission.

ITEMS REQUIRING HUMAN VERIFICATION
- The TS-below-DTW ordering attributed to Yuan et al. (2021) Table B3 (author is a co-author).
- The noisepy-dvv-cloud commit and --use-case of the Gate 1 run; redistribution rights for SCEDC-derived products.
- The seven identical-cell row pairs in the survey CSV and the Snieder2002 row description.
- The pre-correction anticorrelation coefficients (-0.69, -0.45, -0.40): archive their source or drop them.
- Repository public status; README zenodo placeholders; CITATION.cff.

AI-REVIEW DISCLOSURE STAMP (for the Acknowledgements)
> This manuscript was checked with the Denolle Group Pre-Submission Reviewer (v2.4 with Codex/GPT-6, then v2.5 with claude-fable-5-1), an advisory AI tool, through two review iterations prior to submission; the second iteration included local code execution. All findings are reviewed and adjudicated by the author; the tool does not resolve links or confirm results and does not endorse the manuscript's validity.

LEDGER FOR NEXT ITERATION  (manuscript_id=codameter-gji  iteration=2  skill=v2.5  model=claude-fable-5-1)
```
UQ-01        | C2    | Resolved  | RESOLVED                   | src/codameter/uq_measurement.py:76 | Weaver floor omits bandwidth timescale and differs in prefactor.
UQ-02        | C2    | Resolved  | RESOLVED                   | src/codameter/uq_processing.py:220 | Floor variability is substituted for conditional-mean variability.
UQ-03        | C2    | Fair      | PARTIALLY ADDRESSED        | src/codameter/uq_bayes.py:297 | Shared-data pipeline estimates are treated as independent observations.
UQ-04        | C2    | Fair      | PARTIALLY ADDRESSED        | src/codameter/uq_bayes.py:328 | Constructed Cd is not derived or calibrated for shared errors.
UQ-05        | C2    | Fair      | PARTIALLY ADDRESSED        | src/codameter/uq_bayes.py:121 | Bayesian pipeline ignores config axes and changes physical stacking durations.
DET-01       | C2    | Fair      | PARTIALLY ADDRESSED        | src/codameter/deviations.py:174 | RMS, valid supports, reference observables, and requested estimators differ.
DET-02       | C3    | Resolved  | RESOLVED                   | src/codameter/golden.py:508 | Cache inputs depend on warmth and lack generator-code identity.
INV-01       | C2    | Fair      | PARTIALLY ADDRESSED        | src/codameter/inverse/linear_fit.py:430 | Temporal Cd is not connected to diagonal stress inversion or cross-band depth input.
INV-02       | C2    | Resolved  | RESOLVED                   | src/codameter/inverse/linear_fit.py:544; src/codameter/uq_me | Bounds and disconnected reference nodes can have zero reported uncertainty.
SCALE-01     | C3    | Fair      | PARTIALLY ADDRESSED        | src/codameter/uq_bayes.py:299 | Dense Gibbs covariance path is cubic in epoch count.
SCALE-02     | C3    | Resolved  | RESOLVED                   | src/codameter/bench.py:314 | Shard aggregation accepts duplicates and missing shards.
AG-01        | C3    | Resolved  | RESOLVED                   | .claude/skills/codameter-advisor/references/validation_loop. | Public advisor routes fail for three applications and mismatch hard-case targets.
AG-02        | C2    | Resolved  | RESOLVED                   | .claude/skills/codameter-advisor/references/validation_loop. | Elicited constraints and error-bar comparisons lack executable evaluation.
AG-03        | C4    | Resolved  | RESOLVED                   | .claude/skills/codameter-advisor/SKILL.md:3 | Matched synthetic recommendations are described as proven field choices.
EV-01        | C4    | Resolved  | RESOLVED                   | src/codameter/frugalmind.py:299; src/codameter/golden.py:578 | Sparse zero predictions score perfectly on all public cases.
EV-02        | C3    | Fair      | PARTIALLY ADDRESSED        | src/codameter/golden.py:560; src/codameter/frugalmind.py:117 | Truth-free function is not demonstrated sandbox isolation.
EV-03        | C2    | Fair      | PARTIALLY ADDRESSED        | src/codameter/private_golden.py:85; src/codameter/golden.py: | Gold corpus shares generator families and derives thresholds from baseline implementation.
EV-04        | C4    | Resolved  | RESOLVED                   | paper/manuscript_marine.qmd:41 | No executed agent evaluation supports the robust-evaluation claim.
SCI-01       | C2    | Fair      | PARTIALLY ADDRESSED        | paper/manuscript_marine.qmd:446 | SD/SE/network heterogeneity are conflated with one measurement uncertainty.
SCI-02       | C4    | Fair      | PARTIALLY ADDRESSED        | paper/manuscript_marine.qmd:180; paper/manuscript_marine.qmd | Conditional surrogate experiments are generalized to observational dominance and depth.
SCI-03       | C4    | Fair      | PARTIALLY ADDRESSED        | paper/manuscript_marine.qmd:540 | Raw trailing references are presented as common defensible comparisons.
SCI-04       | C6    | Fair      | PARTIALLY ADDRESSED        | paper/manuscript_marine.qmd:309 | Estimator prescriptions and novelty boundary exceed cited conditional evidence.
SCI-05       | C2    | Fair      | PARTIALLY ADDRESSED        | paper/manuscript_marine.qmd:995 | Nominal interval coverage lacks repeated independent validation and chain diagnostics.
SCI-06       | C4    | Fair      | PARTIALLY ADDRESSED        | paper/manuscript_marine.qmd:36; paper/manuscript_marine.qmd: | Depth and operational claims exceed demonstrated results.
SCI-07       | C4    | Fair      | PARTIALLY ADDRESSED        | paper/manuscript_marine.qmd:1133 | Field comparison counts, masks, correlations, and physical attribution are inconsistent.
SCI-08       | C6    | Fair      | PARTIALLY ADDRESSED        | paper/manuscript_marine.qmd:1414 | Abstract-only survey gaps cannot establish full-paper nonreporting.
SCI-09       | C2    | Fair      | PARTIALLY ADDRESSED        | paper/manuscript_marine.qmd:788 | Largest-magnitude and coherence branch selection can bias inference.
SCI-10       | C2    | Resolved  | RESOLVED                   | paper/manuscript_marine.qmd:1345 | Appendix WCC delay sign contradicts the defined dilation convention.
SCI-11       | C4    | Good      | PARTIALLY ADDRESSED        | paper/manuscript_marine.qmd:669 | Universal stack underestimation contradicts reported bias zero crossing.
FIG-01       | C4    | Resolved  | RESOLVED                   | paper/manuscript_marine.qmd:367; PDF p11 | Figure1 WCS trajectory contradicts its caption.
FIG-02       | C5    | Fair      | PARTIALLY ADDRESSED        | paper/manuscript_marine.qmd:1176; PDF pp36–38 | Real-data figures conflict on components, dates, statistics, and counts.
FIG-03       | C5    | Fair      | PARTIALLY ADDRESSED        | PDF pp13,22,25,28,29,32,37 | Missing units, clipped ensembles, occluding legends, and mixed RMS/bias labels.
FMT-01       | C5    | Good      | PARTIALLY ADDRESSED        | paper/manuscript_marine.qmd:10; paper/manuscript_marine.qmd: | Summary paragraphs, figure order, duplicated presentation, and placeholders need revision.
REP-01       | C3    | Resolved  | RESOLVED                   | paper/build.py:124 | Advertised figure build omits six graphics and can preserve stale results.
REP-02       | C3    | Fair      | PARTIALLY ADDRESSED        | paper/data/gate1/README.md:25 | Field products are ignored by Git and comparison driver is external.
REP-03       | C3    | Fair      | PARTIALLY ADDRESSED        | CITATION.cff; src/codameter/workflow.py:696 | Paper experiment settings, version metadata, and replay manifests are incomplete.
COMP-01      | C8    | Fair      | PARTIALLY ADDRESSED        | paper/manuscript_marine.qmd:1427 | Acknowledgements, AI disclosure, and full data access/licensing statements are unfinished.
S-ME.N1      | C2    | Poor      | INTRODUCED-IN-REVISION     | Appendix A | Appendix A (1607-1632): DTW/WTDTW slope statement wrong (slope of l(i)/f_s vs lapse is 1/(
S-FD.1       | C5    | Poor      | INTRODUCED-IN-REVISION     | Fig 8 | Fig 8 panel (d) (demo_6_stacking) collapsed to a sliver after the legend/layout change; (a
S-FD.2       | C5    | Fair      | INTRODUCED-IN-REVISION     | qmd 414, 420-426, 520, 1140-1143, 1161, 1494-1495, 1557-1558 | Sixteen '\\,\\%' outside math render as a literal comma ('0.04,%', '95,%') in the headline
S-FD.3       | C2    | Fair      | INTRODUCED-IN-REVISION     | Table 2, qmd 313-320 | Table 2 says every recovery RMS uses a fixed reference from the first 60% of the record; t
S-RE.2       | C4    | Fair      | INTRODUCED-IN-REVISION     | Fig 13, qmd 963-996; deviations.py:317-330, 475 | Twelve of the 108 multiverse pipelines (MWCS x 4-14 s window) return no epochs; the RMS ra
S-RE.3       | C4    | Fair      | INTRODUCED-IN-REVISION     | qmd 749-754; synthetic_demo.py:2343-2350 | The stacking step-error metric (minimum over 120 post-event epochs minus pre-event median)
S-RE.4       | C2    | Fair      | INTRODUCED-IN-REVISION     | qmd 871-876; synthetic_demo.py:344-351; uq_bayes.py:488-494 | The stated branch rule ('measure both branches ... carry the between-branch difference as
S-RE.5       | C5    | Fair      | INTRODUCED-IN-REVISION     | Fig 15 caption 1355-1366 | Fig 15 caption asserts centred-rule annotations 0.87/0.37/0.62 but the plot prints 0.86/0.
S-CD.1       | C6    | Fair      | INTRODUCED-IN-REVISION     | Appendix C 1677-1679; paper/build_survey.py | '103 rows for 102 publications, Obermann2013 contributing two rows' is false: the two rows
S-ME.N3      | C4    | Fair      | INTRODUCED-IN-REVISION     | qmd 1151 | 'A station clock drift leaves every statistic unchanged' is contradicted at the table's ow
S-ME.N4      | C3    | Fair      | INTRODUCED-IN-REVISION     | qmd 1084-1094 | Hyperprior values (InvGamma(2, 1e-8) for tau^2 and s^2, Gamma(2, 1e-10) for lambda), chain
S-AB.N1      | C4    | Fair      | INTRODUCED-IN-REVISION     | abstract 38-41 | 'reproduces a published dv/v product' overstates a shape agreement after matched smoothing
S-DI.R1      | C4    | Fair      | INTRODUCED-IN-REVISION     | qmd 1516-1517 | The pre-correction anticorrelations r = -0.69, -0.45, -0.40 are cited to the v0.4.0 releas
S-RP.1       | C3    | Fair      | INTRODUCED-IN-REVISION     | figures.py:66-79 | Figure sidecars record git HEAD without a dirty-tree flag or source digest; nine figures r
S-RP.2       | C3    | Fair      | INTRODUCED-IN-REVISION     | qmd 1701-1721 | Data availability names no tag, commit or archive; the committed artifacts come from five
S-RP.3       | C3    | Fair      | INTRODUCED-IN-REVISION     | qmd 1710-1712 | 'python -m codameter.calibration reproduces Table' is not the command that produced it (th
S-RP.4       | C3    | Fair      | INTRODUCED-IN-REVISION     | bench.py:202-216, 332-379 | Shard provenance is keyed on the unbumped version string, so pre- and post-fix shards merg
S-AB.N2-N5   | C4/C5 | Good      | INTRODUCED-IN-REVISION     | abstract | Abstract: temporal C_d named as the depth input where a per-band covariance is meant; 'fix
S-IN.11-12   | C5    | Good      | INTRODUCED-IN-REVISION     | Introduction | NoisePy uncited at first body use (178); 'advisor skill' undefined jargon (180).
S-CO.12-14   | C4/C7 | Good      | INTRODUCED-IN-REVISION     | Conclusions 1549-1561 | 'up to two orders of magnitude' understates the body; the 'remain unvalidated' sentence mi
S-DI.R2-R6   | C4/C7 | Good      | INTRODUCED-IN-REVISION     | Discussion, depth | Calibration realisations redraw noise on one fixed coda and the text does not say so ('fir
S-FD.6-11    | C5    | Good      | INTRODUCED-IN-REVISION     | figures | Fig 17 caption member counts; Table 2 cites Table 5 before 3-4; Fig 10b and 13b legends co
S-RE.7-9     | C5    | Good      | INTRODUCED-IN-REVISION     | Results | Fig 14 legend labels; stale numbers after regeneration (0.71 vs 0.741; ~93x vs 104x; Fig 1
S-CD.2-3     | C6    | Good      | INTRODUCED-IN-REVISION     | Results 346-348; Appendix C 1696-1697 | Yuan et al. (2021) ranking cited without its regime (|dv/v| <= 0.5%, 0-30% noise); the 've
S-PR.1-40    | C5    | Good      | INTRODUCED-BY-RECALIBRATION | whole manuscript | Scientific-register candidates from the new v2.5 scan (40 hits: 8 in new text, 24 unchange
```

Full subagent blocks: reviews/iter2/block_S-*.md. Change map: reviews/codameter-gji.changes.json. Diff: reviews/codameter-gji.iter2.diff. Manifest: reviews/codameter-gji.review.json (iteration 2).

AUTHOR-REQUESTED (added 2026-09-11, after the iteration-2 synthesis)
AUTH-01 | C7/C6 | Fair | Introduction, Discussion, Conclusions | State the impact more strongly (repurposing seismic sensors to monitor internal rheology and deformation is hard and important) and broaden the framing with engineering and experimental coda-wave interferometry. Candidate references from a 2026-09-11 search, to be verified by the author before use: Planes and Larose, "A review of ultrasonic Coda Wave Interferometry in concrete" (Cement and Concrete Research, 2013); Schurr et al., "Damage detection in concrete using coda wave interferometry" (NDT&E International, 2011); Niederleithinger et al., "Processing ultrasonic data by coda wave interferometry to monitor load tests of concrete beams" (Sensors 18, 1971, 2018, doi 10.3390/s18061971); "Sensitivity of ultrasonic coda wave interferometry to material damage, observations from a virtual concrete lab" (Materials, 2021); "Damage detection at a reinforced concrete specimen with coda wave interferometry" (Materials, 2021); "Estimation of stresses in concrete by using coda wave interferometry to establish an acoustoelastic modulus database" (Sensors, 2020); "Thermo-acoustoelastic determination of third-order elastic constants using coda wave interferometry" (International Journal of Mechanical Sciences, 2024); Gret et al., "Monitoring in situ stress changes in a mining environment with coda wave interferometry" (Geophysics, 2006); Singh et al., "Coda wave interferometry for accurate simultaneous monitoring of velocity and acoustic source locations in experimental rock physics" (JGR Solid Earth, 2019, doi 10.1029/2019JB017577); "Material state awareness for composites, part I: precursor damage analysis using ultrasonic guided coda wave interferometry" (Materials, 2017). Already cited and relevant: Snieder et al. 2002 (Science), Hadziioannou et al. 2009, Weaver et al. 2011, Zotz-Wilson et al. 2019, Olivier et al. 2017, Ouellet et al. 2022, Planes et al. 2016. Gaps: the search found no timber or wood CWI study and no direct concrete-dam CWI study (dam monitoring appears only as a stated possible application in Snieder et al. 2002); treat both as open questions, not as citations.
