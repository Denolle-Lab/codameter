# Revision plan, iteration 3

Owner: Fable (Claude), with Marine Denolle. Created 2026-09-11.
Inputs: the iteration-2 review (`reviews/codameter-gji.iter2.report.md`, ledger `reviews/codameter-gji.review.json`: 24 partially addressed prior findings, 24 introduced-in-revision entries, the S-PR register bucket, and the author-requested item AUTH-01).
Principle: the manuscript stays about the science. Every package below either corrects a scientific statement, makes a result reproducible, or states the paper's impact at the level the results support. Nothing is added that the results do not show.

## Order and ownership

| Package | What | Owner | Size | Closes |
|---|---|---|---|---|
| P0 | Regressions introduced by the revision | Fable | hours | S-ME.N1, S-FD.1, S-FD.2, S-ME.N3/S-RE.6, S-CD.1, S-DI.R1, S-AB.N1-N5, S-IN.11-12, S-CO.12-14, S-RE.7-9, S-FD.6-11 |
| P1 | Science corrections in the results and methods | Fable, Marine adjudicates | days | S-RE.2, S-RE.3, S-RE.4, S-FD.3, UQ-05 (multiverse), DET-01, SCI-05, UQ-03/04 residual, SCI-06/INV-01, SCI-04, SCI-03, SCI-09, SCI-02, S-ME.N4, S-DI.R2-R6 |
| P2 | Impact and application framing | Marine with Fable | days | AUTH-01, SCI-04 (novelty sentence), C7 |
| P3 | Provenance, release and real-data figures | Fable, needs Marine's inputs | days | REP-02, REP-03, S-RP.1-4, FIG-02, SCI-07, COMP-01 (part) |
| P4 | Survey hygiene | Fable, Marine verifies rows | day | S-CD.1-3, SCI-08 |
| P5 | Register pass | Marine | hours | S-PR.1-40 |
| P6 | End matter and disclosure | Marine | hours | COMP-01, FMT-01 (placeholder) |
| P7 | Iteration 3 of the reviewer under the `denolle` profile | Fable | hours | ledger reconciliation |

P0 first: it removes errors the revision itself created. P1 and P2 can run in parallel once P0 is committed. P3 waits on Marine's inputs but its code parts can start now. P4 is independent. P5 and P6 are the author's.

## P0. Regressions introduced by the revision (all Fable)

- [ ] Appendix A (S-ME.N1): restore the DTW/WTDTW statement to "the slope of the lag against lapse is 1/(1+eps) - 1 = dv/v, reported directly"; state the Fourier convention and write phi = -2 pi f dt for MWCS/WCS; replace "every estimator returns eps, mapped exactly" with which estimators apply the exact map (TS, WCC, WTS) and which report the fitted delay slope, first order in eps (MWCS, WCS, DTW, WTDTW). Verify each statement against the code paths named in the block.
- [ ] Fig 8 (S-FD.1): fix `fig_stacking` layout (two-column legend, constrained layout, wider figure), add panel letters to the four tiles, regenerate; or drop tiles a, c, d, which duplicate Figs 5 to 7, and keep (b). Decision for Marine: keep or drop the composite.
- [ ] Comma artefacts (S-FD.2): move every `\,\%` into math or write `\%` at the 16 sites; grep the qmd for `\\,\\%` outside `$...$` and rebuild; check the PDF text for ",%".
- [ ] "A station clock drift leaves every statistic unchanged" (S-ME.N3/S-RE.6): "changes no coverage by more than 0.015 and adds no shared bias; the drift lowers the peak coherence, so s falls from 11.7 to 10.9".
- [ ] Survey denominator (S-CD.1, part of P4 but a one-line text fix now): "103 rows for 103 publications" pending the key fix.
- [ ] Pre-correction coefficients (S-DI.R1): archive the pre-correction comparison output under `paper/data/gate1/` if it exists in the noisepy-dvv-cloud smoke outputs, else drop the three numbers and keep the qualitative statement.
- [ ] Abstract (S-AB.N1-N5): "matches the shape of a published product after matched smoothing (r 0.83 to 0.99 on 357 to 579 days), with amplitudes that differ by up to a factor of two at one station"; "a per-band covariance of the same construction" for the depth sentence; drop "fixed scoring support and null-change penalty" or define them in the Introduction; parenthesise the list of choices; add the two-orders-of-magnitude spread.
- [ ] Introduction (S-IN.11-12): cite NoisePy at first use; "processing-choice advisor" with a one-clause gloss instead of "advisor skill".
- [ ] Conclusions (S-CO.12-14): "more than two orders of magnitude (0.02 to 2.8 percent) across 108 pipelines on one synthetic volcano scenario"; reword the "remain unvalidated" sentence (temporal: untested; cross-band: not constructed; shared errors: demonstrably invisible); gloss "target" and "member".
- [ ] Stale numbers after regeneration (S-RE.8): 0.741 percent at 1 day; Fig 9 caption 104x; Fig 1 panel (c) title "both phase methods fail"; give L for the single realisation (39 d) and the 200-run mean (30 d).
- [ ] Figure captions and legends (S-FD.6-11, S-RE.7, S-RE.9): Fig 17 member counts; Table 2 cites Section 5 not Table 5; Fig 10b and 13b legends outside; Fig 14 legend labels to match the caption and "encloses 95 percent of member epochs"; Fig 12 bar label "uncumulated trailing reference"; Fig 13 band drawn as lines or inset; move interpretive caption text to prose; note that two deviations beat the baseline.

Acceptance: PDF rebuilds; no ",%" in the text; Fig 8 legible at print size; Appendix A statements each traced to a code line in the commit message.

## P1. Science corrections

- [ ] Multiverse on the daily grid (UQ-05 residual, S-RP R5, S-RE.2): make `deviations.multiverse` stack daily CCFs and decimate only the output, as `run_processing_ensemble` does; rerun (about 15 min); report n = 96 valid pipelines, name the failing MWCS x 4 to 14 s combination and its cause, count it in the panel annotation and the Sobol basis; update the Section 4 numbers and Fig 13 from the new sidecar. Expect the Sobol ranking to move; report the new one.
- [ ] Step-error metric (S-RE.3): define the metric in the Fig 9 caption; replace the post-event minimum with a robust drop estimate (post-window median or a fitted step); regenerate demo_18; rewrite the Section 3.6 direction statement from the new sidecar. Marine to confirm the estimator choice.
- [ ] Branch rule (S-RE.4, SCI-09): rewrite as a recommendation and state that the present pipeline fits both branches jointly with no branch term in C_d; delete "preferring the branch of greatest change is a researcher's judgement". Implementing per-branch measurement with a between-branch term is deferred and said so.
- [ ] Reference datum per experiment (S-FD.3/S-RE.1/S-ME.N2): split the Table 2 row: generating noise-free reference for the per-choice figures (best-case numbers), first-60 percent stack for OAT, multiverse and Bayes, the five named schemes for Section 3.5; add the estimator defaults (MWCS/WCC 6 s windows, 3 s step; DTW gamma 0.3, max lag 0.8 s).
- [ ] DET-01: reject or label the inversion-reference combinations that ignore the estimator and stack; apply the coherence gate consistently across the reference axis or state the asymmetry; report common-support RMS with availability for the OAT sweep; add paired-seed replicates (three seeds) to the OAT figure with a spread. Regenerate demo_10.
- [ ] SCI-05 residual: state hyperpriors, chain length, burn-in, thinning, seeds and the MIN_COHERENCE rule in the Bayes section (S-ME.N4); add a split-member coverage check (fit s on half the members, score the other half) and a two-chain convergence diagnostic (split-chain R-hat on tau^2, s^2, lambda) to `codameter.calibration`; rerun the clean scenario with them; say that realisations redraw noise on one fixed coda (S-DI.R2) in text and table caption.
- [ ] UQ-03/04 residual: add a duplicate-configuration invariance test and a whitened-residual check of R on the clean runs (a script that reports the autocorrelation of C_d-whitened member residuals); state the result; keep the working-likelihood wording.
- [ ] Depth section (SCI-06/INV-01): delete the density-field "documented extension (Section discussion)" sentence or make it a stated future extension; reword "The width of C_m(z) is the deliverable" and "inherits the temporal correlation and common-mode structure of C_d" to "inherits whatever correlation the supplied per-band covariance carries"; reconcile "in development" (1200) with "implemented" (1230) as "implemented, not evaluated here"; fix the `uq_measurement` and `uq_depth` docstrings that still promise the loop is closed.
- [ ] Estimator prescriptions (SCI-04, S-CD.2): make Table 4 line 1017 agree with Results 345-348; state the Yuan et al. (2021) regime after Marine confirms Table B3.
- [ ] Trailing reference (SCI-03): Table 3 row and the "Scale of effect" sentence to name the ablation; Fig 12 bar label.
- [ ] Synthetic framework (SCI-02): "single-scattering solution" versus "multiply-scattered coda" wording; "every departure ... is an artefact of the processing, not of the data" to exclude additive noise; RT-inspired envelope wording.
- [ ] Discussion (S-DI.R3-R6): two-band ensemble sees one imposed dv/v on the synthetic; name the comparator for "more than the measurement noise"; "committed as produced by the cloud run".

Acceptance: every changed number traces to a regenerated sidecar; the calibration table regenerates from archived runs; tests pass.

## P2. Impact and application framing (AUTH-01)

Marine's brief: the impact should be stated more strongly. Repurposing seismic sensors to monitor internal rheology and deformation is hard and important, and the applications reach beyond the four monitoring targets named now.

- [ ] Introduction: one paragraph stating the impact directly: what it means to turn a passive sensor network into a monitor of internal rheology and deformation, why that is hard (the measurement is a small relative change buried in processing choices), and why the paper's contribution (choice accounting plus a calibrated covariance) is what makes such a monitor trustworthy.
- [ ] Application breadth: a paragraph connecting the same measurement to the engineering and experimental CWI literature, with verified references. Candidates from the 2026-09-11 search (verify DOIs and read before citing): Planes and Larose 2013 (review of ultrasonic CWI in concrete); Schurr et al. 2011 (damage detection in concrete); Niederleithinger et al. 2018 (load tests of concrete beams, doi 10.3390/s18061971); the 2021 Materials virtual-concrete-lab and reinforced-specimen studies; the 2020 Sensors acoustoelastic-modulus study; the 2024 thermo-acoustoelastic third-order-constants study; Gret et al. 2006 (in situ mine stress); Singh et al. 2019 (experimental rock physics, doi 10.1029/2019JB017577); the 2017 Materials composites study. Already cited: Snieder et al. 2002, Hadziioannou et al. 2009, Weaver et al. 2011, Zotz-Wilson et al. 2019, Olivier et al. 2017, Ouellet et al. 2022, Planes et al. 2016.
- [ ] Gaps to state honestly or search further: the search found no timber or wood CWI study and no direct concrete-dam CWI study; dam monitoring appears only as a possible application in Snieder et al. 2002. Marine to decide whether to search engineering venues (Structural Health Monitoring, NDT&E International, Construction and Building Materials) or to name these as open applications.
- [ ] Discussion and Conclusions: carry the strengthened impact statement through, within what the results show (the calibration limits stay).
- [ ] Guardrail: the reviewer's C4 check applies to the new text; the profile's novelty appetite is "defend-heterodox", not "unbounded".

## P3. Provenance, release, real-data figures

- [ ] Marine: the noisepy-dvv-cloud commit and `--use-case` of the Gate 1 run; redistribution rights for the SCEDC-derived products; the archive target.
- [ ] Fable: archive the 2 to 4 Hz daily products with sha256 and a licence file; cite SCEDC and the Clements and Denolle 2023 data release with DOIs (S-RP.2); write an in-repo generator for the comparison figure (Fig 15) from the archived products and comparison.json with corrected bars (S-RE.5/S-FD.4/S-FD.5); keep the interferogram and warm-up figures external and say why (CCFs not archived).
- [ ] Fable: sidecar dirty-tree flag and generator source hash (S-RP.1); generator hash and commit in bench rows and `check_shards` (S-RP.4); a `figures --check` mode; state the calibration invocations in Data availability (S-RP.3); bump the version, tag a release from a clean tree after regenerating every figure and the calibration table at that tag, deposit to Zenodo (release.yml), update CITATION.cff and the README placeholders (REP-03).

## P4. Survey hygiene

- [ ] Fix the key collision in `paper/build_survey.py` (compare the row DOI with the references.bib DOI even when the key exists; disambiguate to Obermann2013b); regenerate survey.bib and appendix_table.tex; "103 rows for 103 publications"; reconcile lines 161, 787 and the caption (S-CD.1).
- [ ] Report the verified reporting rates per field for the full-text dv/v rows with a coding rule separating an error estimate from a QC threshold; say that 21 rows are abstract-derived and excluded (S-CD.3, SCI-08).
- [ ] Add search dates, queries and inclusion rules (one sentence each).
- [ ] Marine: verify the seven identical-cell row pairs and the Snieder2002 row description.

## P5. Register pass (Marine)

The 40 S-PR candidates in `reviews/iter2/block_S-PR.md`, each with one word-swap; the anthropomorphism cluster in the new Bayes and Discussion text first (lines 1083, 1125, 1147, 1163, 1488). Author's call throughout.

## P6. End matter and disclosure (Marine)

Funding, contributions, thanks; the AI-review disclosure stamp from the iteration-2 report (two iterations); the collaboration record `review/HUMAN_AI_COLLABORATION.md` as the basis of the AI-assistance statement; Zenodo DOI once P3 deposits.

## P7. Iteration 3

Run the reviewer in reconciliation mode under `profiles/denolle.md` with a diff against c10a108; the ledger is `reviews/codameter-gji.review.json` at iteration 2.

## Log

- 2026-09-11: plan written from the iteration-2 review; author profile created; AUTH-01 added to the ledger.
