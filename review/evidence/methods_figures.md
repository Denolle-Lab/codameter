# Methods, results, and figure audit

Scope: `paper/manuscript_marine.qmd` and its existing PDF.
Review date: 2026-09-10. Author profile: default.
Target: GJI research/methods article. First focused review.
No manuscript or production source was edited.

Three focused passes followed the supplied skill references.
S-ME preceded S-RE, which preceded S-FD.
Code reads checked selected scientific claims and figure construction.
This evidence file does not replace independent reproduction.

## Strengths

- The central reproducibility question is scientifically valuable.
- The exact stretching convention is explicitly defined.
- Synthetic ground truth enables direct algorithmic error measurements.
- The paper separates component and network aggregation.
- The reference discussion acknowledges important alternative workflows.
- The real-data comparison caught an internally consistent sign error.
- Figure colours usually encode interpretable quantities and categories.
- The reporting checklist would benefit observational studies.

## S-ME: Methods

Six questions: who yes; what yes; when partial.
Where partial; how partial; why partial.
Software/version inventory: partial. Uncertainty treatment: substantial but uncalibrated.

### Checklist

| ID | Status | Evidence |
|---|---|---|
| S-ME.1 | PASS | Controlled recovery design, qmd178–241. |
| S-ME.2 | FAIL | Delay conventions and uncertainty objects conflict; see M2/M3/M7. |
| S-ME.3 | PARTIAL | Baseline choices are motivated, qmd854–867. Priors and estimator parameters remain underspecified. |
| S-ME.4 | PARTIAL | Appropriate for conditional sensitivity experiments. Physical and probabilistic claims exceed this design. |
| S-ME.5 | FAIL | Coverage and shared-data dependence remain unestablished; M1–M3. |
| S-ME.6 | PARTIAL | Uniform stretching is explicit, qmd214–221. Common-mode identifiability and kernel approximations need treatment. |
| S-ME.7 | PARTIAL | Stations and archive named, qmd1114–1147. Exact filtering, joins, exclusions, and waveform manifest need disclosure. |
| S-ME.8 | PARTIAL | Execution sequence understandable. Exact parameter tables and comparison operators absent. |
| S-ME.9 | PARTIAL | codameter v0.4.0 named, qmd1430. NoisePy/dependency versions absent in methods. |
| S-ME.10 | PARTIAL | Readable framework. Several terms denote incompatible statistical objects. |

### M1. Major: the covariance is not derived from the likelihood

Locations: qmd973–1014; PDF31–32; `uq_bayes.py:294–344`.

The likelihood treats configuration residuals as conditionally independent.
However, configurations process the same underlying waveforms.
Their errors therefore share substantial observational information.
Increasing configuration count does not create independent measurements.

The returned covariance is constructed after Gibbs sampling.
Code335 uses the observed cross-configuration sample standard deviation.
Code336 estimates another within-method standard deviation.
Code337 adds both variances under total-variance terminology.
Code344 adds a rank-one term using fitted tau.

Observed cross-configuration spread already contains measurement noise.
It also contains different temporal filtering and offsets.
Adding within-method variance can therefore double-count uncertainty.
Moreover, tau describes between-configuration constant offsets in Eq2.
It does not identify bias shared by every configuration.
An identical bias across configurations leaves their spread unchanged.
The added common-mode term needs independent calibration or priors.

Required: define the downstream estimand and joint sampling model.
Represent shared errors and configuration transfer operators explicitly.
Derive covariance under that model, including cross-band blocks.
Report prior sensitivity and dependence on configuration duplication.
A posterior predictive covariance differs from mean-estimation uncertainty.
Neither is automatically the uniquely correct downstream object.

### M2. Major: nominal coverage is asserted without calibration

Locations: qmd995–1026; PDF32; `uq_bayes.py:251–263,328–344`.

One displayed synthetic cannot establish nominal repeated-sampling coverage.
Temporally correlated epochs are not independent simulation replicates.
The manuscript supplies no replicate count or coverage uncertainty.
It also omits chain diagnostics and sensitivity to hyperpriors.
The second-difference prior can smooth genuine abrupt changes.
A constant configuration offset cannot represent transient-specific failures.

Required: independent seeded experiments across held-out truth classes.
Report bias, RMSE, coverage, interval width, and failure rates.
Evaluate 68%, 95%, and simultaneous-band coverage separately.
Stratify by coherence, transient timing, reference, and source perturbation.
Include posterior predictive checks and convergence diagnostics.
Avoid calling broad bands “honest” before those checks.

### M3. Major: SD, SE, and measurement error are conflated

Locations: qmd446–480,1392–1402; PDF13–15 and Appendix B.
Code: `synthetic_demo.py:1640–1675`.

SD describes dispersion; SE describes an estimator's precision.
Their square-root-N ratio is an algebraic distinction.
It does not establish uncertainty miscalibration by itself.
The claim that any network bar describes mean precision
is directly contradicted by the included SD convention.

The synthetic introduces real pair-dependent amplitude variability.
Specifically, pair_scale varies by 15% before adding noise.
Between-pair scatter consequently mixes heterogeneity and measurement error.
Weights further change the network estimand when sensitivity varies.
The weighted effective count assumes more than unequal weights.
Shared stations and shared noise require covariance between pairs.

Required: define finite-network mean versus population mean explicitly.
Separate spatial variability from within-pair observational uncertainty.
Use Var(weighted mean)=aᵀΣa for normalized weights a.
Demonstrate interval calibration before claims about statistical significance.
Report hypotheses, reference uncertainty, and temporal dependence.

### M4. Major: synthetic physics and inference targets need separation

Locations: qmd180–222,494–521,775–794,1039–1087.
Code: `synthetic_demo.py:129–167,190–200,2076–2095,2461–2467`.

The surrogate is useful for controlled measurement experiments.
It is not full waveform propagation through heterogeneous structure.
The implementation softens the diffuse onset and broadens the delta.
It also freely scales the ballistic contribution.
It omits the exact relative normalization of ballistic/diffuse terms.
The manuscript should call this an RT-inspired envelope.
“Single scattering” conflicts with the described multiply scattered coda.

The “two-layer” example assigns separate signals to separate bands.
Its code contains no depth model or sensitivity kernel.
Recovering those signals demonstrates spectral separation under that construction.
It does not establish actual layer resolution or frequency-depth tolerances.
Likewise, branch-specific truth is imposed directly on each branch.
Physical branch kernels are asserted rather than calculated.

Required: state these conditional constructions and their limitations.
Add an independently generated heterogeneous-wavefield benchmark before generalization.
Vary envelope, illumination, attenuation, geometry, and waveform decorrelation.
Classify additive-noise departures as stochastic observational error too.
Known truth does not make every residual a processing artefact.

### M5. Major: reference comparisons include different observables

Locations: qmd540–613,626–629,947–948; PDF17–19,30.

Fixed references change the velocity-change zero point.
The manuscript correctly identifies this at qmd549–557.
However, raw RMS still ranks those offsets as errors.
Real-data validation removes equivalent offsets through demeaning, qmd1140–1142.
Apply a consistent target convention in both comparisons.

The paper acknowledges no surveyed uncumulated trailing workflow.
Nevertheless, Table3 labels moving references a common deviation.
Raw trailing increments should be identified as an ablation.
A trailing-average residual is also not a one-day increment.
Simply cumulatively summing it does not generally invert averaging.

Required: compare registered common-reference observables and transient recovery.
Benchmark cumulative-adjacent and segmented-reference approaches actually used.
Keep deliberately incomplete workflows outside “reasonable pipeline” priors.

### M6. Major: branch selection advice contradicts its own experiment

Locations: qmd784–794; PDF25, Fig10.

The simulation demonstrates maximum-amplitude selection bias.
The subsequent recommendation permits maximum selection nevertheless.
Matched sign and similar coherence do not eliminate this bias.
Coherence estimated from the same observations is data-dependent.
It cannot automatically be called independent of the answer.

Required: predefine branch handling using external physical information.
Alternatively evaluate selection on independent or held-out data.
Report both branches and their covariance before combining them.
Any selection rule needs conditional coverage and false-alarm checks.

### M7. Major: Appendix WCC delay sign contradicts epsilon

Locations: qmd95–119 and1345–1347.

For delayed current c(t)=r(t−d), the stated correlation peaks
at positive tau=d in integral c(t)r(t−tau)dt.
The introduction defines positive epsilon for delayed current arrivals.
Thus delay versus reference lapse has positive epsilon slope.
The Appendix instead writes delta_t=−epsilon*t_i.
An analytic single-pulse example exposes this inconsistency.

Required: define all delay and Fourier conventions consistently.
Trace each estimator's fitted slope into physical dv/v.
State the finite-change mapping for each regression coordinate.
Propagate errors through dv/v=−epsilon/(1+epsilon).
Its Jacobian magnitude is 1/(1+epsilon)².
The Appendix's small-error scaling concerns epsilon, not automatically dv/v.

### M8. Major: depth claims precede a demonstrated inversion

Locations: qmd33–37,1031–1087,1291–1301; PDF33–35.

The summary promises illustrated depth propagation.
The depth section instead describes work still in development.
No depth-recovery figure, resolution test, or covariance comparison appears.
The discrete kernel matrix also needs integration weights.
A depth covariance requires two depth coordinates, plus time indexing.
Per-time single-band covariance alone cannot supply cross-band uncertainty.

Required: either scope this as future work consistently,
or include the actual forward model and synthetic inversion.
Show kernels, resolution, posterior covariance, and model uncertainty.
Distinguish shear-wave speed from shear modulus and density effects.
Fluid-substitution assumptions need explicit parameterization and identifiability analysis.

### M9. Major: omitted experimental details prevent fair comparisons

Locations: qmd178–241,357–399,840–970,973–993.

Most figure captions omit seeds, SNR definitions, and replicates.
Estimator-specific windows, lag limits, regularization, and grids matter.
The code supplies many details absent from the manuscript.
For example, Fig1 uses different bands and windows across panels.
See `synthetic_demo.py:1397–1425`.

Required: provide a machine-readable experiment manifest per figure.
Include exact configuration sets, priors, masks, and metric definitions.
Distinguish RMSE, mean bias, residual scatter, and drop error.
Version the numerical results alongside the plots.

## S-RE: Results

Quantitative reporting: partial. Figure/table order: fails first-citation order.
Results deliberately mixes empirical results with interpretation and recommendations.
Treat section organization as minor; scientific contradictions remain major.

| ID | Status | Evidence |
|---|---|---|
| S-RE.1 | PASS | qmd309–325 previews the parameter experiments. |
| S-RE.2 | PARTIAL | Clear axes; repeated overview plots interrupt progression. |
| S-RE.3 | PARTIAL | Table2, subsection numbers, and “Scale of effect” paragraphs repeat results. |
| S-RE.4 | PARTIAL | Explicitly mixed explanatory results. Interpretive blocks listed below. |
| S-RE.5 | PARTIAL | External comparisons embedded in reference subsection. |
| S-RE.6 | FAIL | Replicates, uncertainty on metrics, and masked counts mostly absent. |
| S-RE.7 | FAIL | Error-band interpretation unvalidated; see M1–M3. |
| S-RE.8 | PARTIAL | All main figures cited. Fig8 discussed before Fig5, qmd499–510. |
| S-RE.9 | PARTIAL | Fig17 is called optional supplement but stays main-text. |

Interpretive blocks, minimum 16: qmd381–385,395–399,416–427,
450–456,475–482,496–512,547–557,559–566,599–613,650–653,
665–673,741–752,775–794,811–821,859–867,890–898.
This is a block inventory, not exhaustive sentence counting.
External comparison clusters, minimum six: qmd449–450,471–473,
574–585,587–597,645–647,725–727.
No language/register revision is necessary solely for mixed structure.

### R1. Major: Figure1 contradicts its recovery claim

Locations: qmd367–385; PDF11, Fig1c.
Code: `synthetic_demo.py:1381–1388,1415–1425,1466–1469`.

The red dashed WCS curve visibly jumps to positive values.
The true landslide change becomes strongly negative.
The caption nevertheless claims unwrapped WCS tracks the truth.
Colour assignments in code confirm the red curve is WCS.
The method discussion should describe the plotted failure accurately.
Regenerate the numerical trace and derive claims directly from it.

### R2. Major: RMS is repeatedly called bias

Locations: qmd869–876; PDF28, Fig12 title and horizontal axis.

The panel title describes injected bias.
Its horizontal axis measures RMS error against truth.
RMS mixes bias and variance, with different scientific implications.
Report both or label this panel as RMSE throughout.

Table2 is additionally dimensionally consistent but statistically inconsistent.
Its network row compares SE with individual-pair range as RMS.
See qmd335–337 and PDF10.
Replace these with a common metric or separate columns.

### R3. Major: real-data agreement does not validate uncertainty

Locations: qmd1133–1182; PDF36–37, Figs15–16.

A high correlation can coexist with wrong amplitude and uncertainty.
Demeaning and 90-day smoothing further limit the validation target.
681 overlapping days are not 681 independent observations.
Two calendar years contain 730 days before exclusions.
After 150-day burn-in, at most 580 remain within 2018–2019.
The claimed 681 needs reconciliation with the actual date range.
Duplicate joins or external dates are possible, not established here.

The ARV range 0.66–0.92 depends on unspecified joining choices.
Missingness and interpolation require prespecified sensitivity analyses.
Report bias after alignment, slope, RMSE, residual correlation,
and uncertainty calibration against appropriate independent information.
Give station coordinates, masks, dates, components, and join definitions.

The RXH pattern may reflect site or source changes.
An interferogram alone cannot discriminate instrument or processing effects.
“The visual difference is the reason” overstates causal identification.
Check station metadata, response changes, and processing logs.

### R4. Moderate: internally inconsistent stacking conclusions

Locations: qmd669–673; PDF21.

The paragraph says every stack underestimates the drop.
It immediately acknowledges a bias zero crossing after 45 days.
Consequently the asserted universal lower bound is unsupported.
Report signed amplitude error and its scenario-dependent interpretation.

## S-FD: Figures and data presentation

Counts: 17 figures; five main tables; one appendix table.
Eight numbered equation environments, plus unnumbered displayed equations.
No independent colour-vision simulation was performed.
The visual palette appears broadly suitable for quantitative plotting.
Viridis-family and sequential maps avoid rainbow encodings.
Some categorical curves still depend heavily on colour.

Visual inspection: all 17 figure pages inspected at 1800px.
Also inspected title, every main table, and appendix endpoints.
Pages: 1,9,10,11,13,14,15,16,19,21,22,24,25,26,
28,29,30,32,34,35,36,37,38,39,45,55.
These 26 renders are retained under `evidence/figures/`.
Other PDF pages were text-reviewed, not visually inspected.
The existing PDF has 74 pages, dated 2026-08-17.
No fresh manuscript build was performed in this pass.

| ID | Status | Evidence |
|---|---|---|
| S-FD.1 | PARTIAL | Fig8 repeats four stories; Fig17 belongs in supplement. |
| S-FD.2 | PARTIAL | Useful time series and matrices; duplicated synthesis tables. |
| S-FD.3 | FAIL | Early Table1 cites Figs8/11 before Figs2/3. Main prose introduces Fig8 before Fig5. |
| S-FD.4 | PARTIAL | Analytical captions listed below; descriptive scope preferred. |
| S-FD.5 | FAIL | Missing covariance/RMS units; Fig16 lacks amplitude scale. |
| S-FD.6 | PARTIAL | Fig2 shared axes succeed. Fig13 mixes fractions and percentages. |
| S-FD.7 | PARTIAL | Sequential maps suitable; full accessibility simulation not performed. |
| S-FD.8 | PARTIAL | Table2 mixes statistical objects; experiment counts absent. |
| S-FD.9 | FAIL | WCC sign and covariance definitions require corrections. |
| S-FD.10 | PARTIAL | General code link provided; per-figure numerical provenance absent. |

Analytical captions: Figs1,2,3,4,5,6,8,9,10,11,12,13,14,16.
These 14 flags concern clarity and evidential boundaries.
Moving interpretation into prose is optional editorial restructuring.
The contradictions within captions require correction regardless of structure.

### F1. Major: Figure16 identifies conflicting components

PDF37 plot title reads “Daily NZ cross-component CCFs”.
Caption says north-south/east-west, indicating NE correlations.
Source caption: qmd1176–1182.
Resolve component provenance before interpreting station differences.
Add an amplitude colourbar and normalization definition.
Near-zero-lag energy alone does not identify coda windows.
Overlay the actual measured lag windows.

### F2. Moderate: real-data figures retain development annotations

PDF36 Fig15 calls the reference “Clements–Denolle 2022”.
Its caption cites the 2023 product instead.
The plot says “smoothing-matched” while the caption says otherwise.
Displayed r values are 0.86,0.58,0.37.
The text instead emphasizes 0.990,0.68,0.66–0.92.
The caption acknowledges two analyses but forces reader reconciliation.
Show the matched comparison supporting the central claim.
Retain the unmatched comparison as a supplementary sensitivity check.

PDF38 Fig17 title says 5/5 later members.
Its upper panels annotate 4/5 members.
Define whether these annotations describe instantaneous or maximum counts.
Replace “smoke store”, “Gate1 final”, and debugging titles.
Enlarge legends and annotations at final publication size.

### F3. Moderate: legends hide signal and comparison features

PDF13 Fig2a legend covers the recovered trajectory.
PDF22 Fig8 legends cover troughs and the transient.
PDF25 Fig10a legend obscures the largest drop.
PDF32 Fig14a legend covers the negative excursion and bands.
Use shared exterior legends or a dedicated legend strip.
Use direct labels where only a few curves remain.
Add panel letters to Fig8's four separate plots.

### F4. Moderate: clipping conceals the multiverse result

PDF29 Fig13a truncates much of the pipeline ensemble.
Its 10–90% band also exceeds the visible range.
Dense vertical traces obscure both the distribution and event.
The caption admits clipping, which is helpful but insufficient.
Show a full-range inset or separate failure-rate distribution.
Plot a density/quantile summary instead of every failed trajectory.
Label RMS colourbar as fraction or percentage explicitly.
PDF32 Fig14 covariance colourbar also needs squared units.

### F5. Moderate: figure content lacks calibration evidence

Most RMS curves and bars have no replicate uncertainty.
This is not solved by finer graphic styling.
Add independent-seed intervals and declared experiment counts first.
Show coverage-versus-nominal plots for the proposed covariance.
Show cross-band covariance and depth-resolution results if claimed.

### F6. Minor: layout is readable but unnecessarily long

The referee layout provides useful spacing and line numbers.
No gross clipping was observed on the inspected pages.
The running title nearly spans the full page width.
Use an abbreviated running title if the class supports it.
The long survey begins with one row on PDF45.
Consider a separate supplementary table with full provenance fields.
Avoid duplicating Fig8 with four dedicated experiment figures.
Keep main figures focused on testable central contributions.

## Prioritized fixes and hand-off

1. Repair covariance derivation and uncertainty calibration first.
2. Define shared estimands across references, bands, and pairs.
3. Correct estimator, component, and real-data figure contradictions.
4. Add independent synthetic replications and physical transfer tests.
5. Align completed depth/agent claims with demonstrated results.
6. Rebuild plots from versioned numerical output and manifests.

Tier feeds: C2 Poor; C4 Poor; C5 Fair.
C3 methodological completeness: Fair, pending independent reproduction.
These are advisory section-level judgments, not editorial decisions.

Root code audit additionally identified Weaver-floor implementation discrepancies.
Manuscript Appendix qmd1338–1341 includes bandwidth dependence explicitly.
That displayed dependence must match the executed uncertainty function.
The code audit owns the verified dimensional and prefactor evidence.

## Fresh-build visual QA addendum

The reproduction pass subsequently built the current manuscript successfully.
Fresh PDF: `evidence/reproduction_workspace/paper/manuscript_marine.pdf`.
Its metadata records 2026-09-10, with 74 pages unchanged.
The title page now prints 2026-09-10.

Six fresh pages were rendered and visually inspected.
Pages1,11,29,32,36,37 correspond to the title and requested figures.
Renders: `evidence/figures/fresh_page_01.png` and corresponding numbered files.
This supplements the earlier 26-page visual inspection.
The selected figure pages retain their original page numbers.

All checked substantive figure findings persist:

- Fig1c, page11: WCS visibly fails despite its tracking claim.
- Fig13, page29: ensemble clipping and ambiguous RMS units persist.
- Fig14, page32: covariance units remain absent; legend obscures signals.
- Fig15, page36: 2022/2023 and smoothing annotations still conflict.
- Fig15 still displays r=0.86,0.58,0.37 beside different textual results.
- Fig16, page37: NZ title still contradicts the NE caption.
- Fig16 still lacks amplitude normalization and a colourbar.

No inspected issue was resolved by rebuilding the document.
This checks rendering consistency, not fresh numerical figure generation.
See the reproduction evidence for that separate execution scope.
