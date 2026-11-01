# Manuscript scientific and presentation review

**Recommendation: major revision before GJI submission.** The central premise is useful and relevant. Processing choices should be explicit and their effects measured. The present evidence establishes conditional processing sensitivity. It does not yet establish calibrated total measurement uncertainty, depth inference, or robust advisor performance.

Reviewed source: `paper/manuscript_marine.qmd`. The README identifies it as authoritative. The older manuscript files were excluded as stale. The existing PDF has 74 pages, dated 2026-08-17. This review treats the manuscript as a research paper. Its scope exceeds a short letter's intended format.

## Specific strengths

- The exact physical dv/v sign convention is explicit. See source lines 95–125.
- Synthetic experiments make processing assumptions inspectable. See lines 180–222 and the multiverse section.
- The study distinguishes component aggregation from network averaging. That distinction matters for reproducible observations.
- Independent product comparison exposed a consequential sign error. The discussion documents a valuable validation lesson.
- The reporting checklist provides practical community guidance. See lines 1212–1252.
- Source code, tests, and a literature catalogue are available. They provide a strong foundation for revision.

## SCI-01: Define the scientific estimand before uncertainty

**Major.** The square-root-N headline compares different statistical targets. SD describes dispersion; SE describes precision of a mean. Their ratio is largely an algebraic identity. It does not establish conflicting valid significance conclusions.

See lines 446–480, 1392–1402, and Figures 3–4. The network synthetic additionally imposes 15% pair-amplitude heterogeneity. Thus pair spread contains physical variability and observational noise. A weighted network can also change the target average.

State whether the target is a specific pair, a finite-network mean, a population mean, or a depth-weighted physical property. Specify the null hypothesis. For normalized network weights \(a\), propagate \(a^T\Sigma a\). Include dependence from shared stations, reference data, and illumination. Neither SD nor SE universally substitutes for that calculation.

Table 2 compounds the problem. Its network row compares network SE with an individual-pair range under an RMS heading. Replace the mixed metrics with separately named quantities.

## SCI-02: Bound the inference from constructed experiments

**Major.** A processing sweep holds one waveform realization fixed. It can establish conditional sensitivity to the chosen menu. It cannot show that processing generally dominates observational variability. See lines 838–911 and 1207–1209.

Add independent waveforms and noise realizations to estimate both contributions. Use paired seeds when comparing pipelines. Report interactions, failures, and uncertainty on metric differences. Identify the configuration distribution behind each variance attribution.

The two-layer examples assign distinct truths to separated frequency bands. This is a controlled spectral-mixture experiment. It does not establish actual depth resolution. Branch-specific truths are also imposed directly. Their physical sensitivity kernels are not estimated.

Describe the coda envelope as radiative-transfer-inspired. The implementation modifies onset, ballistic scaling, and normalization. Claims about physical transport should distinguish this surrogate from full wave propagation.

## SCI-03: Compare equivalent reference observables

**Major.** Fixed references alter the zero point. Raw trailing-reference outputs have a different temporal response. Comparing both directly against an absolute truth confounds measurement error with the chosen observable.

See lines 540–613 and Table 3. The text acknowledges no surveyed study reports uncumulated trailing outputs. Calling this a common reasonable practice therefore overstates the survey evidence. Present it as a deliberately incomplete ablation.

Define a common datum and target response. Include reference linking or increment inversion used in practice. Match baseline alignment across synthetic and field comparisons. A trailing-average residual is not generally a daily increment; simply accumulating it does not undo its averaging operator.

## SCI-04: Replace universal estimator prescriptions

**Major.** The stretching recommendation needs scenario-specific evidence. The cited seven-method comparison ranks TS noise resistance low and DTW high under its conditions. That does not establish a universal opposite ranking either. It establishes the need to explain different settings. See manuscript lines 309–312, 933–936, and [Yuan et al., Table B3](https://academic.oup.com/gji/article/226/2/828/6224864).

Compare tuned estimators under matched bands, windows, noise spectra, amplitudes, and computational budgets. Distinguish estimator limitations from this implementation's tuning. The strongest potential novelty is joint choice accounting, beyond another seven-estimator comparison.

The branch-selection recommendation also needs revision. Figure 10 demonstrates maximum-selection bias. Lines 788–792 nevertheless permit choosing the largest magnitude and imply coherence selection avoids bias. Coherence is estimated from the same observations. Predefine branch rules or validate selection using independent data.

## SCI-05: Calibration is a missing central experiment

**Submission blocker, alongside implementation corrections.** Figure 14 shows one synthetic realization. The statement that its band restores nominal coverage is unsupported as a repeated-sampling claim. Neither wider intervals nor positive-definite covariance establishes calibration.

The [software audit](02_software_and_uncertainty.md) identifies formula and covariance problems. Fix those first. Then evaluate independent held-out realizations. Report 68% and 95% pointwise coverage, simultaneous coverage where claimed, width, bias, and failures. Separate posterior inference under an assumed model from empirical error coverage under misspecification.

Include common source drift and clock errors. Include errors all pipelines share. Include transient attenuation from stacks and smoothing priors. Show that downstream parameter intervals retain calibrated coverage.

## SCI-06: Match abstract claims to completed evidence

**Major.** Abstract lines 36–43 promise depth propagation and robust advisor evaluation. The depth section and conclusion describe stages still being built. No depth-recovery figure or actual agent-results table supports those promises.

| Abstract claim | Available evidence | Necessary revision |
|---|---|---|
| Individual and combined processing effects | Constructed experiments and factorial sweep | State tested scenarios and conditional scope |
| Square-root-N change in reported uncertainty | SD/SE comparison | Define different estimands and hypotheses |
| Bayesian measurement covariance | Implemented hierarchy and posthoc covariance | Correct derivation and demonstrate calibration |
| Demonstrated depth-error propagation | Equations and implementation framework | Add kernels, recovered profiles, resolution, and coverage |
| Independent California reproduction | Smoothed/demeaned curve comparison | Reconcile data, masks, figures, and metric provenance |
| Laptop-to-cloud scalability | Optimization and execution infrastructure | Add runtime, memory, throughput, and failure measurements |
| Robust advisor evaluation | Skill, synthetic recipes, scorers, tests | Add executed model evaluation after scorer repair |

Either supply the missing evidence or narrow the claims consistently. A covariance interface is a useful deliverable by itself. It should not be described as a completed inference validation.

## SCI-07: Strengthen the observational validation

**Major.** Product agreement is valuable consistency evidence. Correlation alone does not validate amplitude, bias, uncertainty, or physical attribution. Demeaning and 90-day smoothing further narrow what is being validated.

The reported sample count needs reconciliation. For 2018–2019, excluding the first 150 days leaves at most 580 dates. The text reports 681 LJR overlapping days. The reproduction audit finds 578 available LJR product dates after that exclusion. A burn-in applied to older reference history could change this calculation. The manuscript needs that exact interval and mask. Recompute the comparison from an explicit date-and-mask table.

ARV correlations depend on unspecified joining choices. Prespecify the joining, interpolation, smoothing, and exclusion rules. Report each sensitivity analysis separately. Include paired residuals, amplitude slopes, RMS, effective temporal information, and measurement uncertainty.

The RXH interferogram suggests a different waveform history. It does not identify its cause. Check station responses, component labels, clocks, and source changes before physical attribution.

## SCI-08: Audit the literature survey's denominator

**Major for reporting-prevalence claims.** The source distinguishes full-text extraction from abstract-only records. Missing information in an abstract cannot establish nonreporting in the publication. Lines 1414–1423 incorrectly describe apparent underreporting as a lower bound.

Report verified reporting, verified nonreporting, and inaccessible status separately. Supply search dates, queries, inclusion rules, deduplication, and extraction provenance. Reconcile 103 appendix citations against 102 unique citation keys. This may represent multiple rows per publication; it requires a declared study-count definition.

The groundwater discussion also needs narrower attribution. The cited review allows physical hydrological variation. Processing differences are one possible explanation for scatter. Replace the unresolved “Figure x” and specify correlation sign. See lines 140–145 and [Denolle et al., 2025](https://comptes-rendus.academie-sciences.fr/geoscience/articles/10.5802/crgeos.310/).

## Figure and design audit

All 17 figure pages were visually inspected. The title, five main tables, and appendix endpoints were inspected too. In total, 26 pages were rendered. Other pages received text review. No simulated color-vision audit was performed.

An isolated current-source build subsequently produced another 74-page PDF. Six selected pages received fresh visual checks. The Figure 1, 13, 14, 15, and 16 findings persisted. Existing numerical figure assets were reused during compilation.

The referee layout is generally readable. Line numbering and spacing help review. Sequential color maps are sensible. The larger problems are mismatched claims, hidden data, and missing statistical labels.

| Priority | Figure or table | Finding and correction |
|---|---|---|
| Major | Fig. 1c, PDF p11 | Red WCS curve jumps positive; caption says it tracks truth. Reconcile traces, labels, and claim. |
| Major | Table 2, p10 | Network row compares incompatible statistics. Give distinct columns and targets. |
| Major | Fig. 15, p36 | Displayed correlations differ from headline matched analysis. Plot the exact analysis supporting the claim. |
| Major | Fig. 16, p37 | Plot says NZ; caption describes NE. Resolve component provenance before interpretation. |
| Moderate | Fig. 12, p28 | RMS axis is described as bias. Separate signed bias from RMSE. |
| Moderate | Fig. 13, p29 | Ensemble and quantiles exceed axis limits. Add full-range view and failure summary. Label RMS units. |
| Moderate | Fig. 14, p32 | Label covariance in fractional dv/v squared or percent squared. Distinguish empirical error bands from credible intervals. |
| Moderate | Figs. 2, 8, 10, 14 | Legends obscure trajectories, troughs, or uncertainty. Move legends outside data regions. |
| Moderate | Fig. 16 | Add amplitude scale, normalization definition, and measurement windows. |
| Moderate | Fig. 17, p38 | Title says 5/5 members; panels say 4/5. Explain timing or reconcile. Remove development labels. |
| Minor | Fig. 8 | Add panel letters. Consider removing duplication with dedicated experiment figures. |
| Minor | Tables and figure calls | Repair first-citation order. Early tables reference later figures first. |

Prefer vector exports for line plots and text. Keep raster interferograms at adequate final-size resolution. Use redundant line styles for estimator categories. Export numerical values and experiment metadata beside every figure.

A tighter main-paper sequence would follow the evidence:

1. Define the observation target and processing operators.
2. Compare conditional effects under matched configurations.
3. Quantify replicated sensitivity and interactions.
4. Derive and calibrate the measurement model.
5. Validate against independent observational products.
6. Demonstrate depth or advisor results only if retained.

Place the complete survey and secondary diagnostics in supplements. This is organizational advice, not a journal length violation.

## GJI format, references, and end matter

The approximately 362-word source summary meets the current 500-word research-paper limit. GJI requires a single summary paragraph. The source contains three. The 250-word limit applies to Express Letters. A Data Availability statement is required. AI assistance should be disclosed in the cover letter and manuscript. See [current GJI instructions](https://academic.oup.com/gji/pages/general_instructions).

Acknowledgements remain a placeholder at line 1436. Finalize authorship, funding, contributions, and relevant disclosures. The available data statement omits the field products and external generation dependencies. A future Zenodo archive is not a presently reviewable versioned release. Avoid treating a DOI alone as a substitute for complete accessible artifacts.

The bibliography contains 129 unique cited entries. No missing or duplicate citation keys were found. Nine entries include Denolle, 7.0% overall. Main-text citations include eight such works among 59, 13.6%. No inflation was established. The references span 1951–2026. GJI, JGR Solid Earth, and GRL together account for 53.5%.

These are awareness signals, not diversity scores. Geographic author coverage was not quantified. Study location was not treated as author identity. No gender, race, or nationality inference was performed.

The complete nine-scope findings remain in [paper sections](evidence/paper_sections.md), [methods and figures](evidence/methods_figures.md), and [reproducibility](evidence/reproducibility.md).
