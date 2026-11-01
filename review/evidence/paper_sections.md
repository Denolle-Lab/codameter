# Focused paper findings

Date: 2026-09-10.
Target: GJI research paper, with methods emphasis.
Source: `paper/manuscript_marine.qmd`.
Profile: pre-submission-reviewer `profiles/default.md`.
Scopes: S-AB, S-IN, S-DI, S-CO, S-CD.
Mode: sequential focused review; first-pass evidence.
These are raw findings for the review orchestrator.
Source files were not changed.
Line references refer to the QMD source.
Code, figures, and reproduction have separate reviewers.

## Strengths

- The processing-choice question has clear practical relevance. See 127–158.
- The exact sign convention is explicitly defined. See 95–125.
- The multiverse connects methods with uncertainty propagation. See 838–1027.
- Independent comparison exposed a consequential sign error. See 1270–1289.
- The reporting checklist supports inspectable observational workflows. See 1212–1252.
- Stress conversion limitations are acknowledged explicitly. See 1296–1301.

## S-AB: title and abstract

Inventory: title present; abstract present; no plain-language summary.
Abstract length: 362 whitespace-delimited source tokens, approximately.
Problem, approach, result, and significance are all present.
The quantitative headline is the square-root-N uncertainty ratio.

1. **S-AB.1 PASS / MINOR FORMAT.** Length satisfies GJI's 500-word cap.
   GJI requires one paragraph for research-paper summaries.
   This source contains three paragraphs, lines 10–45.
   Join paragraphs after resolving the scientific overclaims.
   [GJI author instructions](https://academic.oup.com/gji/pages/General_Instructions).
2. **S-AB.2 PASS.** The processing uncertainty gap is explicit, 13–18.
3. **S-AB.3 PARTIAL.** The approach appears at 22–36.
   The treatment of pipeline choices needs qualification.
   Specify which configurations share the same physical estimand.
4. **S-AB.4 PARTIAL / MAJOR.** The numeric headline needs its estimand, 27–31.
   Standard deviation describes dispersion among observations.
   Standard error describes precision of an estimated mean.
   Their square-root-N ratio is definitional under independence.
   It does not establish two valid significance answers.
   Name the tested null and the target quantity.
   State independence requirements and pair dependence limitations.
5. **S-AB.5 PARTIAL / MAJOR.** Operational readiness exceeds demonstrated scope, 20–21, 39–43.
   The body presents three stations and computational optimizations.
   It does not present operational reliability or agent evaluation.
   Separate demonstrated capability from intended future deployment.
6. **S-AB.6 PASS.** The ensemble covariance contribution is identifiable, 33–36.
   Its calibration and probabilistic interpretation remain separate questions.
7. **S-AB.7 PARTIAL / MINOR.** The title fits processing sensitivity, line 2.
   “Reproducibility cost” could imply measured reproducibility failure rates.
   Define that phrase through sensitivity and incomplete reporting.
   A title change is optional, following scope clarification.
8. **S-AB.8 FAIL / MAJOR.** Several promised results lack paper evidence.
   See the claim trace below.
9. **S-AB.9 FAIL / MAJOR.** Depth demonstration and agent robustness overreach.
   Lines 36–43 promise results absent from the body.
   Add completed experiments or narrow those claims.
10. **S-AB.10 PARTIAL / MINOR.** Delta-v/v is defined clearly.
    Explain covariance notation when retaining it in the abstract.
    “Agent-ready” needs an observable capability definition.
11. **S-AB.11 N/A.** No plain-language summary is supplied.

### Abstract claim trace

| Claim location | Claimed result | Body support | Verdict |
|---|---|---|---|
| 20–21 | Scalable, uncertainty-aware, agent-ready observations | Optimizations, 959–971; deployment, 1114–1201 | Partial; readiness criteria absent |
| 22–24 | Individual and combined processing effects | Results; multiverse, 838–911 | Shown on selected synthetic scenarios |
| 24 | Estimator families fail differently at large changes | Estimator section; `fig:methods`, 359–409 | Supported conditionally; verify plotted numbers separately |
| 24–26 | Component averaging changes identical-pair estimates | Aggregation; `fig:aggregation`, 412–440 | Supported on constructed component mixture |
| 27–31 | Significance changes by approximately square-root-N | Uncertainty section; appendix, 1392–1402 | Demonstrated convention difference; interpretation overstates equivalence |
| 33–36 | Ensemble becomes Bayesian data covariance | Bayesian model; `fig:bayes`, 973–1027 | Implemented claim; derivation/calibration requires methods audit |
| 36–37 | Errors propagated through depth inversion | Framework, 1031–1087 | UNSUPPORTED as demonstrated result |
| 37–40 | California product reproduced across pipelines | Deployment; `fig:realdata-validation`, 1133 onward | Partial; waveform agreement differs from uncertainty validation |
| 40–41 | Portability and laptop-to-cloud scalability demonstrated | 959–971; proposed cloud pipeline, 1120–1128 | Partial; no scaling curve or deployment success statistics |
| 41–43 | Advisor robustly evaluated against golden data | Intro mentions scoring, 171–176 | UNSUPPORTED in manuscript; no evaluation protocol/results section |
| 43–45 | Reproducible uncertainty-aware measurement package | Whole paper; availability, 1429–1432 | Conditional on reproduction and calibration results |

Depth contradiction is explicit, not inferred from missing figures.
Lines 1033–1037 describe executable stages as under development.
Line 1064 instead says depth covariance is implemented.
Lines 1298–1301 simultaneously promise delivery and future testing.
Conclusions 1317–1318 again describe the depth stage being built.

Top fixes: align delivered scope; define uncertainty estimands.
Then add measured agent and deployment evaluation results.
Tier feed: C1 Good; C4 Fair; C5 Good; C7 Fair.

## S-IN: introduction

Swales moves: M1 PASS, 72–93; M2 PASS, 127–145.
M3 PASS structurally, 147–176; scientific scope needs tightening.
Five questions: problem, prior work, limitations, aim, setup present.
Length: 107 source lines, including three displayed equations.
The introduction remains motivated rather than purely historical.

1. **S-IN.1 PARTIAL / MINOR.** History needs precise attribution, 80–85.
   Piton de la Fournaise was not the technique's discovery.
   Distinguish eruption forecasting from earlier passive monitoring.
   Merapi monitoring predates the cited 2008 deployment.
   The 2006 reference already exists in `references.bib`.
   [Sens-Schönfelder and Wegler, 2006](https://agupubs.onlinelibrary.wiley.com/doi/abs/10.1029/2006gl027797).
2. **S-IN.2 PARTIAL / MAJOR.** The novelty boundary is unsupported, 135–145.
   “Cumulative effect” needs an explicit literature-search boundary.
   Existing estimator comparisons already test multiple processing dimensions.
   Claim the particular joint design and covariance contribution.
   Avoid implying earlier uncertainty quantification was absent.
3. **S-IN.3 PARTIAL / MAJOR.** Stated scope exceeds shown work, 160–176.
   Depth illustration and advisor evaluation need corresponding results.
   Distinguish reproduction of curves from calibrated error reproduction.
4. **S-IN.4 PASS.** The central objective is explicit, 151–158.
5. **S-IN.5 PASS, WITH QUALIFICATION.** Operational relevance is clear, 80–93.
   “Determining early warning” requires operational decision evidence.
   “Tens of tailings dams” requires deployment-count evidence.
   The cited studies support applications and monitoring potential.
   They do not establish every stronger operational claim.
   [Çubuk-Sabuncu et al., 2021](https://agupubs.onlinelibrary.wiley.com/doi/abs/10.1029/2020GL092265).
   [Ouellet et al., 2022](https://doi.org/10.1038/s43247-022-00629-w).
6. **S-IN.6 PARTIAL / OPTIONAL CLARITY.** The convention derivation interrupts motivation.
   Lines 95–125 could move into the synthetic framework.
   Retain the physical sign definition in the introduction.
   This is structural advice, not a length violation.
7. **S-IN.7 PARTIAL.** General-to-specific progression is otherwise clear.
8. **S-IN.8 PARTIAL / MINOR.** Define SNR before line 123.
9. **S-IN.9 PARTIAL / MAJOR EVIDENCE.** Hydrological attribution overstates the source, 140–145.
   “Figure x” remains an unresolved placeholder.
   “Direct correlation” obscures the reported anticorrelation sign.
   Processing differences do not exclude genuine geological differences.
   The cited review discusses both hydrological and physical variability.
   Present processing as one possible source of scatter.
   Identify the actual figure and support attribution quantitatively.
   [Denolle et al., 2025, sections 2 and 5](https://comptes-rendus.academie-sciences.fr/geoscience/articles/10.5802/crgeos.310/).
10. **S-IN.10 PASS.** All introduction citation keys resolve locally.
    Bibliographic resolution does not validate each associated claim.

Novelty assessment: plausible, bounded methodological contribution.
The strongest novelty is joint processing-sensitivity accounting.
It is not the seven-estimator comparison by itself.
Yuan et al. already compare those seven methods.
They use heterogeneous full-wave simulations and depth-dependent perturbations.
[Yuan et al., 2021](https://academic.oup.com/gji/article/226/2/828/6224864).

Top fixes: bound novelty; align scope; repair hydrological attribution.
Tier feed: C1 Good/Fair; C6 Fair; C7 Good.

## S-DI: discussion

Moves: summary YES; interpretation YES; implications YES; future YES.
Comparison: self YES; foundational global methods YES; competing results limited.
Alternatives: PARTIAL. Explicit synthetic limitations: INSUFFICIENT.
The named “three responses” actually contains five responses.
This is minor organization, lines 1210–1291.

1. **S-DI.1 PASS.** Opens with the central finding, 1207–1209.
2. **S-DI.2 PASS.** Connects observations with reporting and propagation.
3. **S-DI.3 PARTIAL.** No explicit falsifiable hypothesis was specified.
   Give a bounded answer for the scenarios actually tested.
4. **S-DI.4 PARTIAL / MAJOR.** Comparison remains mostly prescriptive, 1255–1268.
   Compare the proposed uncertainty with independent established approaches.
   State what improves beyond Clarke, Weaver, and Yuan.
5. **S-DI.5 FAIL / MAJOR.** Discuss contradictory estimator performance evidence.
   The manuscript promotes stretching for low SNR, 309–312.
   Table 933–936 repeats this as best practice.
   Yet cited Yuan Table B3 ranks TS noise resistance low.
   The same table ranks DTW noise resistance high.
   Those rankings themselves depend on the tested scenario.
   Explain the different noise, windows, tuning, and targets.
   Compare tuned estimators under matched conditions before generalizing.
   [Yuan et al., 2021, Table B3](https://academic.oup.com/gji/article/226/2/828/6224864).
6. **S-DI.6 FAIL / MAJOR.** Dominance over data is not identified, 1207–1209.
   A conditional processing sweep fixes the observed waveform.
   It cannot partition variability across possible observed waveforms.
   Add replicated wavefields, source changes, and noise realizations.
   Separate physical heterogeneity from preprocessing sensitivity explicitly.
7. **S-DI.7 FAIL / MAJOR.** Missing limitations qualify the central method.
   No representativeness guarantee exists for the pipeline prior.
   Shared waveforms induce dependence among pipeline estimates.
   An ensemble can share bias while remaining tightly clustered.
   Different bands can target different physical properties.
   Selecting ensemble members using truth risks optimistic calibration.
   State these limitations beside the covariance recommendation, 1255–1262.
8. **S-DI.8 PARTIAL.** Interpretations sometimes become universal prescriptions.
   “More honest” at 1259 needs demonstrated coverage conditions.
   Marginalizing configurations alone does not guarantee calibrated errors.
9. **S-DI.9 PARTIAL / MINOR.** New historical numbers appear, 1277–1279.
   The negative validation correlations need an archived result table.
   Move the diagnostic before/after comparison into Results.
10. **S-DI.10 FAIL / MAJOR.** Reported significance is overgeneralized, 1216–1218.
    Distinguish mean precision, population spread, and common systematic error.
    Neither SD nor SE universally replaces the other.
    State the desired inferential target before computing significance.
11. **S-DI.11 PARTIAL / MAJOR.** Depth delivery remains internally contradictory.
    Lines 1298–1301 claim delivery and ongoing construction together.
    Propagated covariance cannot repair misspecified sensitivity kernels.
    Retain depth as a qualified roadmap unless demonstrated.

Independent validation remains a substantial positive finding.
The sign-error example is concrete and scientifically useful.
Avoid claiming agreement with published products proves physical truth.
Agreement establishes consistency against one independent processing product.

Top fixes: add limitations; compare competing methods; define calibration.
Tier feed: C4 Fair; C6 Fair; C7 Good/Fair.

## S-CO: conclusions

Pols framework: six elements present; substantiation is partial.
Score: 6/7, using only fully supported elements.
Independent readability YES; new results NO; verbatim copying NO.

1. **S-CO.1 PASS.** The paragraph is independently understandable, 1305–1318.
2. **S-CO.2 PASS.** It restates the processing uncertainty objective.
3. **S-CO.3 PASS.** The reproducibility problem remains clear.
4. **S-CO.4 PASS.** The synthetic estimator comparison is identified.
5. **S-CO.5 PARTIAL / MAJOR.** The square-root-N conclusion needs conditions.
   Lines 1308–1310 conflate spread with mean uncertainty.
   State the estimand and dependence assumptions explicitly.
6. **S-CO.6 PARTIAL / MINOR.** Add a genuinely empirical quantitative result.
   The current headline mostly repeats an algebraic identity.
   Prefer a bounded processing-effect or held-out coverage result.
7. **S-CO.7 PASS.** Reporting and covariance recommendations are concrete.
8. **S-CO.8 PASS.** No new numerical result appears here.
9. **S-CO.9 PARTIAL / MAJOR.** Covariance propagation is necessary but insufficient.
   Lines 1314–1316 imply it ensures honest depth uncertainty.
   Include kernel uncertainty and calibrated measurement-model assumptions.
10. **S-CO.10 PASS.** No empty opening or verbatim restatement identified.
11. **S-CO.11 FAIL / MAJOR.** Contribution conflicts with the abstract.
    Here the depth stage is still being built.
    The abstract says its error propagation is illustrated.

Top fixes: align depth status; qualify significance; substantiate empirically.
Tier feed: C1 Good; C4 Fair; C7 Good/Fair.

## S-CD: citation and idea diversity

These signals are surfaced, never scored as diversity quotas.
Identity inference was disabled by the default author profile.
The inventory is `review/evidence/citation_inventory.json`.
Counts combine QMD citations and the included appendix table.
Email text was excluded from citation parsing.

1. **S-CD.1 INFORMATIONAL.** Nine of 129 references include Denolle.
   That is 7.0% of the combined reference list.
   Main QMD citations: eight of 59, or 13.6%.
   These counts use explicit author strings, not inferred identity.
   There is no demonstrated self-citation inflation.
2. **S-CD.2 INFORMATIONAL.** Years span 1951–2026; median 2017.
   Counts: 1950s 1; 1980s 1; 1990s 3.
   Counts: 2000s 18; 2010s 65; 2020s 41.
   The list combines foundational and recent research.
3. **S-CD.3 INFORMATIONAL.** GJI supplies 25 references, or 19.4%.
   JGR Solid Earth supplies 22; GRL supplies 22.
   Those three venues comprise 53.5% of references.
   There are 39 raw venue/metadata categories.
   Shannon entropy is 4.14 bits over those categories.
   Two entries lack journal fields, including one book.
   Venue labels were not fully standardized across historical names.
4. **S-CD.4 CANNOT ASSESS COMPLETELY.** Author-country metadata are absent locally.
   No complete OpenAlex affiliation enrichment was performed.
   Study location is not author affiliation or nationality.
   Do not derive demographic coverage from surnames or sites.
5. **S-CD.5 PARTIAL INFORMATIONAL.** The combination is interdisciplinary.
   Seismology, scattering physics, statistics, and rock physics appear.
   Formal OpenAlex field counts were not computed.
6. **S-CD.6 INFORMATIONAL.** Main QMD has 59 unique cited works.
   Those works receive 127 citation occurrences.
   Clarke appears 12 times; Weaver 8; Obermann2013 7.
   Thirty-four main-text works appear once.
   Seventy works appear only through the survey appendix.
   That is expected for an explicitly cited evidence catalogue.
   It is not independently evidence of ornamental citation.
7. **S-CD.7 DISABLED.** No gender, race, or nationality inference.
8. **S-CD.8 MIXED / STRENGTH.** Methodology and multiverse analysis combine productively.
   No co-citation baseline was computed for quantitative novelty.
   Existing seven-estimator comparison is conventional prior work.
   Joint choice accounting is the stronger candidate contribution.
9. **S-CD.9 PASS.** Cross-disciplinary framing is scientifically legitimate.
   Statistical validity, not unfamiliarity, determines the required revisions.

All 129 unique bibliography entries are cited somewhere.
There are no duplicate keys or missing citation keys.
The appendix contains 103 citations to 102 unique keys.
This may reflect multiple rows for one publication.
Reconcile “103 studies” against unique study definitions.
The dedicated survey audit should determine the correct denominator.

The survey caveat also reverses its uncertainty direction.
Lines 1414–1423 distinguish full-text and metadata-only extraction.
Missing metadata cannot establish nonreporting in inaccessible papers.
Apparent nonreporting can therefore be inflated, not understated.
Report verified and inaccessible denominators separately.
This is an evidence-quality concern, not a diversity penalty.

## Primary-source verification scope

Checked sources support bounded comparisons, not exhaustive novelty claims.
The search did not establish absence of prior joint analyses.
The main references below resolve through publisher sources.

- [GJI instructions](https://academic.oup.com/gji/pages/General_Instructions): summary requirements.
- [Yuan et al., 2021](https://academic.oup.com/gji/article/226/2/828/6224864): seven-method comparison and Table B3.
- [Sens-Schönfelder and Wegler, 2006](https://agupubs.onlinelibrary.wiley.com/doi/abs/10.1029/2006gl027797): earlier passive volcano monitoring.
- [Denolle et al., 2025](https://comptes-rendus.academie-sciences.fr/geoscience/articles/10.5802/crgeos.310/): groundwater anticorrelation and physical alternatives.
- [Çubuk-Sabuncu et al., 2021](https://agupubs.onlinelibrary.wiley.com/doi/abs/10.1029/2020GL092265): Reykjanes monitoring study.
- [Ouellet et al., 2022](https://doi.org/10.1038/s43247-022-00629-w): instrumented Canadian tailings-dam study.

Suggested synthesis priority: C4 scope, then probabilistic validity.
Preserve the multiverse premise while testing its calibration.
