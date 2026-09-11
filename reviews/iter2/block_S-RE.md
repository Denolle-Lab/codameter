SUBAGENT S-RE  scope: Results (Sec 3 all, Sec 4, Sec 5 reported results, Sec 7)  changed-scope re-dispatch: yes
INVENTORY: 33 hunks in scope (15 content, 18 cosmetic); Fig 1, Table 6, calibration numbers all reproduce from sources; other sidecars match except drifts in S-RE.8; citation order FAIL persists on unchanged text; 13 interpretive sentences on changed spans (mostly acceptable caveats).
RECONCILIATION:
SCI-01 | PARTIALLY ADDRESSED | estimands defined (517-520, Table 2); network row removed. Residual: pair covariance named not computed; Table 2 datum wrong for Section 3 (S-RE.1). Poor -> Fair.
SCI-03 | PARTIALLY ADDRESSED | ablation wording (1030-1032, 941-945, 775-777). Residual: no cumulated/stitched benchmark; Table 3 row 395-396 and "Scale of effect" 704-707 still price "moving"; Fig 12 bar label. Fair.
SCI-04 | PARTIALLY ADDRESSED | 345-348 conditional; Fig 1c RMS per estimator. Residual: Table 4 line 1017; no tuned comparison; estimator defaults unstated (MWCS/WCC 6 s/3 s; DTW gamma 0.3, 0.8 s). Fair.
SCI-05 | PARTIALLY ADDRESSED | 200 realisations, prefixed margin, values verified. Residual: coverage is in-sample (same members s and Cd were fitted on; calibration.py:150-171); no convergence diagnostic; 68% fails margin (stated). Poor -> Fair.
SCI-07 | PARTIALLY ADDRESSED | matched-rule numbers and driver; 681 explained. Residual: Fig 15 annotations 0.86/0.58/0.37 vs caption 0.87/0.37/0.62; bars 3.1x too large; L1299-1300 "caps the correlation near 0.7" conflicts with Table 6 (centred 0.865); RXH site-change attribution without metadata (1377-1378). Poor -> Fair.
SCI-09 | PARTIALLY ADDRESSED | rule predefined (871-874). Residual: not what the pipeline does (S-RE.4); 865-866 "researcher's judgement" remains. Fair.
SCI-11 | PARTIALLY ADDRESSED | contradiction gone; rerun confirms zero crossing 45-60 d for SNR 4. Residual: direction misread (S-RE.3). Good.
R1 RESOLVED (residual: panel c title); R2 RESOLVED (residual: Fig 7 caption "absolute bias"); R3 PARTIAL (as SCI-07); R4 PARTIAL (as SCI-11).
INTRODUCED-IN-REVISION:
S-RE.1 | Fair | Table 2 316-320 | "fixed reference from the first 60%" true only for Section 4; Section 3 demos use the noise-free s.ref (best-case numbers a field pipeline cannot reach), 0.8-yr stack, 15%/whole stacks | state the datum per figure.
S-RE.2 | Fair | Fig 13 caption 984-996, text 963-970 | 12 of 108 pipelines return no epochs (MWCS x 4-14 s window); RMS range, SD and Sobol computed on 96; panel count excludes them | report n=96, name the failing combination, count it.
S-RE.3 | Fair | 749-754 | step-error metric (min over 120 post-event epochs minus pre-event median, minus truth's) negative means the drop is over-estimated; -5.4% at 1 day is extreme-value bias | define the metric, use a robust drop estimate, state the direction correctly.
S-RE.4 | Fair | 871-876 | "measure both branches ... carry the between-branch difference as a term of C_d" not implemented: branch="both" fits one stretch over |t|; Cd has no branch term | implement or rewrite as a recommendation.
S-RE.5 | Fair | Fig 15 caption 1355-1366 | annotations mismatch; bars 3.1x too large on an external figure | regenerate in-repo from paper/data/gate1 or drop and keep Table 6.
S-RE.6 | Good | 1147-1148 | "leaves every statistic unchanged" false beyond SE | "changes no statistic by more than 0.015".
S-RE.7 | Good | Fig 14 caption vs legend labels; legend covers ensemble | relabel; move.
S-RE.8 | Good | stale numbers after regeneration: L743 0.71 vs 0.741; Fig 9 caption ~93x vs 104x; Fig 1c title; L1132 L≈40 d single realisation vs 30 d mean | update from sidecars.
S-RE.9 | Good | Fig 12 caption "band and gating are minor" | two deviations score below the baseline (0.022, 0.027 vs 0.032%) | state it.
TIER FEED: C2 Fair (from Poor); C4 Fair (from Poor); C5 Fair.
TOP FIXES: regenerate Fig 15 and fix L1299; disclose n=96; Table 2 datum + estimator parameters; step metric direction + branch rule; in-sample caveat + convergence + soften "unchanged".
