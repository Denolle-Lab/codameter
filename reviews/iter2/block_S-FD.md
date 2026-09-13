SUBAGENT S-FD  scope: figures, tables, captions, equations  changed-scope re-dispatch: yes
INVENTORY: 17 figures (14 generated, 3 external); 9 tables; 9 numbered equations; citation order FAIL (Table 1 cites Fig 8/11 before Figs 2-7; Table 2 cites Table 5 before 3-4; Table 6 never cited, pre-existing); colour audit PASS for maps, concern for Fig 12 red/orange rule and Fig 16 no scale.
RECONCILIATION:
SCI-01 | PARTIALLY ADDRESSED | Table 2 defines estimands (304-338); mixed row deleted; text 517-534 names a^T Sigma a. Residual: not computed; no null hypothesis; Fig 3 caption unchanged presents the identity as a finding; Table 2 datum wrong for Section 3 (S-FD.3).
FIG-01 | RESOLVED | caption 441-444 and text 419-426 match demo_1_methods.npz (TS 0.0047, WTS 0.0096, WCC 0.046, WTDTW 0.085, DTW 0.163, MWCS 2.91, WCS 3.76 %). Residual: panel (c) title still "MWCS cycle-skips" only; comma artefacts (S-FD.2).
FIG-02 | PARTIALLY ADDRESSED | Fig 16 caption NZ matches plot; Table 7 and text match comparison.json exactly. Residual: Fig 15 caption claims centred-rule annotations 0.87/0.37/0.62 but plot shows RXH 0.58 (matches no rule), title still "smoothing-matched", caption describes error bars not in the legend; Fig 17 title 5/5 vs panel counts.
FIG-03 | PARTIALLY ADDRESSED | Fig 12 relabelled RMS; Fig 13 colourbar units and off-axis count; Fig 14 units; legends moved on Figs 1, 2, 10a. Residual: Fig 13a band invisible (clipped); fraction/percent mixed; Fig 14a legend covers the band for t<1.6 yr; Fig 16 no colourbar; Fig 8 regressed (S-FD.1).
FMT-01 | PARTIALLY ADDRESSED | one-paragraph abstract; no placeholders in text. Residual: Acknowledgements placeholder; citation order unchanged; Fig 8 duplicates Figs 5-7; Table 6 never cited.
INTRODUCED-IN-REVISION:
S-FD.1 | C5 Poor | Fig 8 panel (d) demo_6_stacking regenerated 7bfdcef | axes collapse to a sliver: 4-column legend below + title + tight_layout in a 4x3-in figure; panels (a),(b) legends overprint x labels; no panel letters | widen or ncol=2 with constrained layout; add (a)-(d); or keep only tile (b).
S-FD.2 | C5 Fair | qmd 414, 420-426, 520, 1140-1143, 1161, 1494-1495, 1557-1558 (16 sites, all new text) | "\,\%" outside math renders as "0.04,%", "95,%" | put inside math or write "\%".
S-FD.3 | C2 Fair | Table 2 qmd 313-316 | "fixed reference from the first 60% of the record" true only for Section 4; Section 3 figures use Synth.ref (noiseless), fig_reference uses first 0.8 yr, Section 3.5 sweeps references | split the datum row by experiment.
S-FD.4 | C5 Fair | Fig 15 caption 1358-1361 | annotations 0.86/0.37/0.58 on the plot vs caption 0.87/0.37/0.62; 0.58 matches no rule; title "smoothing-matched" | state the run's own undocumented rule or regenerate from comparison.json.
S-FD.5 | C5 Fair | Fig 15 caption 1356-1366 | describes within-measurement error bars not in the legend and not visible | delete or plot.
S-FD.6 | C5 Good | Fig 17 caption 1408-1411 | member-count reading cannot produce "3/4/5", "0/2/3/4/5" | describe as the set of counts over the epochs, or regenerate.
S-FD.7 | C5 Good | Table 2 qmd 332 | cites Table 5 before 3-4 | cite Section 5.
S-FD.8 | C5 Good | Fig 10b, Fig 13b legends | cover the SNR 1-1.5 points / clip the tallest bar | move outside.
S-FD.9 | C5 Good | Fig 14 caption 1177-1185 | "encloses the individual members" (members leave the band; coverage 0.956); legend labels differ from caption terms | "encloses 95% of member epochs"; align labels.
S-FD.10 | C5 Good | Fig 12 bar label "Reference scheme: moving" vs text "uncumulated trailing reference"; Fig 13 caption band invisible | relabel; inset or band edges.
S-FD.11 | C5 Good | captions of Figs 12, 13, 14c, 16, Table 5, Table 2 C_d row | interpretive caption text | move to prose.
TIER FEED: C2 Fair; C5 Fair (would be Poor if left).
TOP FIXES: regenerate Fig 8; fix 16 comma artefacts; Fig 15/17 captions vs plots; Table 2 datum + Table 5 citation; citation order.
