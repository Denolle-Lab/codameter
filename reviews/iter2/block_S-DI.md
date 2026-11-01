SUBAGENT S-DI  scope: Discussion (1417-1543), depth (1195-1279)  changed-scope re-dispatch: yes
INVENTORY: moves M1-M4 present; five responses match "the following responses"; limitations paragraph 1479-1499 states pipeline-prior menu, shared-error blindness, band-vs-estimand, floor as lower bound, and what pointwise tests do not establish.
RECONCILIATION:
AG-03 | RESOLVED (scope decision) | SKILL.md "assesses conditionally"; abstract 45-48; intro 180-186.
SCI-02 | PARTIALLY ADDRESSED | dominance made conditional (1419-1426); but calibration realisations redraw noise on one fixed coda (calibration.py:100, synthetic_demo.py:1240 seed=0) and the text never says so; "first step" overstates (R2).
SCI-04 | PARTIALLY ADDRESSED | Results 343-348 and intro 143-146 qualified; Table tab:bp-measure line 1017 still says "robust at low SNR" citing Yuan2021 (contradiction).
SCI-06 | PARTIALLY ADDRESSED | narrowed in abstract, Discussion 1536-1539, Conclusions 1566, deployment title; but depth 1251-1253 "executable version is a documented extension (Section discussion)" has no such extension and no density field in uq_depth.py; depth 1232-1233 "The width of C_m(z) is the deliverable" reads as delivered.
S-DI.4 PASS; S-DI.5 PARTIAL (table row); S-DI.6 PASS; S-DI.7 PASS; S-DI.8 PASS; S-DI.9 PARTIAL (see R1); S-DI.10 PASS (tab:bp-network 1037-1038 "ambiguity in significance" unchanged text); S-DI.11 PARTIAL.
INTRODUCED-IN-REVISION:
S-DI.R1 | C4 minor-moderate | 1516-1517 | "recorded in the codameter v0.4.0 release notes": the notes do not contain r=-0.69,-0.45,-0.40 | archive the pre-correction output and cite it, or drop the coefficients.
S-DI.R2 | C4 minor | 1423-1426 | "first step toward it" implies varied wavefields; realisations vary noise only | say so; add to the table caption.
S-DI.R3 | C7 minor | 1487-1491 | "marginalised only over pipelines that target one estimand" vs the two-band ensemble | add that both bands see one imposed dv/v on the synthetic.
S-DI.R4 | C4 minor | depth 1226-1233 | "does not supply its cross-band entries" contradicts retained "inherits the temporal correlation ... of C_d" | reword.
S-DI.R5 | C4 minor | 1419-1422 | "by more than the measurement noise does" has no comparator | name the coherence floor or drop.
S-DI.R6 | C7 low | 1494-1496 | "are archived" vs Data availability "not yet deposited" | "committed as produced by the cloud run".
TIER FEED: C4 Fair; C6 Fair; C7 Good.
TOP FIXES: R1; R2; table row 1017; depth 1251-1253 and 1232-1233; R3/R5.
