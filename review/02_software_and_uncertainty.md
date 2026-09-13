# Software and measurement uncertainty audit

The project exposes important, usually hidden processing choices. Seeded waveforms, explicit configurations, and modular estimators support inspection. Those strengths do not establish calibrated measurement uncertainty. Several implemented uncertainty calculations require correction before scientific use.

Evidence refers to the audited checkout, commit `b6dbbd03ad3a9e7b8daac3847a470b93b6918cc8`. Line numbers refer to original source files. Executable probes and numerical outputs reside in [evidence](evidence/). No scientific source was changed.

## What each uncertainty object actually represents

| Object | Current meaning | Necessary qualification |
|---|---|---|
| One seeded recovery RMS | Error for one waveform realization | Not expected bias or calibrated uncertainty |
| OAT/factorial variation | Sensitivity to the selected configuration menu | Depends on menu, metric, seed, and time support |
| Across-pipeline SD | Disagreement among transformations of shared data | Cannot reveal an artifact shared by every pipeline |
| `mu_cov` | Posterior covariance under the implemented hierarchical likelihood | Shared-data independence assumptions require justification |
| `Cd` | Posthoc covariance using fitted scales and an exponential kernel | Not the sampled posterior covariance or a derived mixture covariance |
| Depth posterior | Conditional inference given kernels, priors, and supplied covariance | Does not include uncertain kernels automatically |

Determinism answers whether execution repeats. Calibration answers whether uncertainty predicts errors. They require separate validation.

## UQ-01: The Weaver floor is dimensionally incomplete

**Submission blocker.** `src/codameter/uq_measurement.py:76–124` calculates

\[
\sigma^2=\frac{1-CC^2}{2CC^2}
\frac{6\sqrt{\pi/2}}{\omega_c^2(t_2^3-t_1^3)}.
\]

The denominator has units of seconds. The numerator is dimensionless. Therefore the returned quantity lacks dimensionless fractional-velocity units.

Weaver et al.'s Gaussian-spectrum expression includes a bandwidth timescale, here denoted \(T_B\):

\[
\operatorname{rms}(\epsilon)=\frac{\sqrt{1-X^2}}{2X}
\sqrt{\frac{6\sqrt{\pi/2}\,T_B}
{\omega_c^2(t_2^3-t_1^3)}}.
\]

The code also differs in the squared coherence prefactor. Establish the bandwidth convention and branch-count normalization explicitly. See [Weaver et al., equation 20, preprint page 7](https://arxiv.org/pdf/1103.1785).

The dimensional probe gives a factor `0.0316228` under equivalent time-unit reexpression. This diagnoses the formula, not an advertised milliseconds API. More directly, its arguments contain no bandwidth information. Equal center frequencies and coherence therefore produce identical floors for differently wide bands.

**Required correction:** implement and document the spectral correlation timescale. Derive the prefactor for the actual measurement setup. Validate against independent noise realizations across bandwidths. Recalculate all dependent uncertainty results, including depth examples. A fitted global scale cannot establish bandwidth-specific calibration.

## UQ-02: Variability of error bars is misclassified

**Submission blocker for this propagation path.** `uq_processing.py:220–266` adds `var(floors)` to `mean(floors**2)`. A fixed supplied `band_bias` adds its square too.

For a mixture with identical conditional means,

\[
\operatorname{Var}(Y)=E_c[\sigma_c^2],
\qquad \operatorname{Var}_c(E[Y\mid c])=0.
\]

Different conditional precisions do not imply different conditional means. The extra variance therefore has no stated probabilistic basis. A known fixed bias belongs in the mean correction. Its square contributes to mean-squared error, not centered variance, unless an explicit random-bias model is supplied.

Our two-choice probe gives `1.79521e-6` for the zero-mean mixture variance. The implementation returns `2.46206e-6`, about 37% larger. This is a mathematical counterexample, not waveform calibration.

**Required correction:** compute conditional central estimates by reprocessing. Alternatively, specify and validate a bias distribution. Keep variance, bias, and MSE separately named.

## UQ-03: The hierarchical likelihood counts shared evidence repeatedly

**Major.** `uq_bayes.py:297–317` sums independent precisions across configurations and epochs. Yet every configuration transforms the same CCF matrix. Overlapping bands, windows, stacks, and the reference share noise.

The implementation fits all outputs jointly as repeated observations. It does not implement a discrete mixture over alternative pipelines. These statistical constructions are different. A constant configuration offset cannot represent configuration-specific smoothing, transient attenuation, or different depth sensitivity.

The same inverse-gamma hyperparameters govern `tau²` and dimensionless `s²`. With shape 2 and scale `1e-8`, their prior mean is `1e-8`. Calling these priors weakly informative needs scale-specific justification. Report prior-predictive behavior and sensitivity, especially for the purported error-floor multiplier.

**Required correction:** define the observation target before combining pipelines. Use a joint error model, calibrated generalized likelihood, or a clearly defined weighted model mixture. Model each pipeline's temporal and depth response where necessary. Check invariance to duplicating identical configurations. Compare independent waveform ensembles, not just additional pipelines.

## UQ-04: `Cd` is an uncalibrated covariance construction

**Major.** `uq_bayes.py:328–344` samples `mu_cov`, then separately constructs

\[
C_d=D R(L)D+\tau^2\mathbf1\mathbf1^T,
\quad D_{tt}^2=s^2\overline{\sigma_k^2(t)}
+\operatorname{Var}_k[m_k(t)].
\]

The module introduction calls `Cd` the posterior covariance at lines 37–39. The dataclass correctly distinguishes those objects at lines 175–186. The documentation therefore contradicts itself.

Across-member variance includes variation from within-method noise. Adding a noise floor may double-count it. Configuration offsets already contribute to member variance; adding `tau²` needs a separate derivation. Between-configuration offsets cannot identify bias shared across all configurations. The fitted correlation length is also treated as known downstream.

The common-artifact probe uses four identical sinusoidal measurements. The true signal is zero. It yields:

| Diagnostic | Result |
|---|---:|
| RMS estimation error | `0.00212136` fractional dv/v |
| Median `sqrt(diag(Cd))` | `0.0000599802` |
| Epochs containing zero within ±2 SD | `2/30` |

This is a constructed failure case. It is **not** an estimated population coverage rate. It disproves the general claim that agreement plus this covariance necessarily covers shared errors.

**Required correction:** choose a clear target distribution. Derive its covariance without counting components twice. Calibrate against shared source drift, timing errors, reference contamination, and waveform-model mismatch. Distinguish posterior credible intervals from prediction or measurement-error intervals.

## UQ-05: Configuration and time semantics differ between engines

**Major.** `uq_bayes.run_processing_ensemble`, lines 125–157, always creates a fixed reference. It ignores supplied `reference` and `gate`. The probe confirms identical outputs for fixed/gated and moving/ungated configurations. Their labels are identical too.

Both the Bayesian ensemble and multiverse subsample CCFs before stacking. See `uq_bayes.py:121–129` and `deviations.py:344–354`. A ten-record stack at three-day cadence spans 27 elapsed days. It is not a ten-day trailing stack. A 45-record moving reference similarly changes its physical duration. Cadence changes the experiment, not merely computation cost.

`gibbs_dvv` constructs second differences in index space. Its latent posterior ignores actual time intervals. Adding a 1,000-day gap leaves the posterior mean bitwise identical. Times enter the later covariance calculation, producing inconsistent time treatment.

The ensemble also clips peak coherence upward to 0.5. Low coherence cannot then increase the floor without bound. This needs rejection or explicit failure handling.

**Required correction:** use one canonical pipeline implementation. Reject unsupported options. Specify stack/reference durations in physical time. Stack before decimating output, or convert durations explicitly. Either support irregular timestamps properly or reject them.

## DET-01: Deterministic comparisons need matched targets and support

**Major.** `deviations.metrics:243–255` compares raw reference-relative outputs with absolute synthetic truth. `golden._rms:578–596` instead removes a baseline offset. Rankings therefore depend on which metric path executes.

Each configuration also supplies its own valid mask. Gating or missing estimates can change the evaluated epochs. The drop metric selects a post-event minimum, increasing sensitivity to noise and search duration. The first-order variance fractions are valid sensitivity summaries for a complete balanced design. Dropping failed runs can unbalance that design.

The reference implementation adds further confounding. At `deviations.py:213–216`, selecting `inversion` always calls a stretching implementation. The requested estimator and stack are not honored. Gating applies only to fixed-reference stretching when a peak correlation exists.

**Required correction:** define a shared datum, observation operator, and evaluation interval. Report common-support recovery alongside availability. Report rejected epochs and event misses. Use repeated paired seeds for contrasts. Retain failed configurations in failure-rate summaries. Explicitly list unsupported combinations.

## DET-02: Golden cache changes numerical inputs

**Major for exact reproducibility; numerical impact still bounded only at input level.** `golden.py:508–553` hashes recipes but not generator code. A cold call returns newly generated float64 CCFs. A warm call reads float32 arrays.

The probe finds maximum difference `4.7683e-7`. No claim is made that this difference materially changes published estimates. However, cold and warm runs are not bitwise identical. Generator edits can also leave old arrays under unchanged recipe hashes. Manifest regeneration deliberately bypasses that cache, so the scorer and oracle may consume different artifacts.

**Required correction:** include generator, dependency, and dtype versions in cache identities. Return a consistent dtype. Write caches atomically. Pin immutable input checksums and retain benchmark thresholds separately from estimator updates.

## INV-01: Downstream uncertainty is not connected consistently

**Major.** `inverse/linear_fit.py:430–502` accepts diagonal errors only. It cannot directly consume temporal `Cd`. `uq_depth.invert_depth_profile:165–225` accepts cross-band covariance for one depth inversion. A temporal covariance is a different-shaped object. Neither fact alone implements a joint time-band-depth inference chain.

The bound-constrained linear solver also zeros covariance rows at active bounds, lines 544–549. A parameter constrained to be nonnegative can have a one-sided uncertain posterior. An optimizer touching zero does not establish zero uncertainty. The audit probe returns exactly zero variance at such a bound.

`global_reference_inversion:419–429` uses a pseudoinverse without checking graph connectivity. For three epochs and only one connected pair, the isolated epoch receives zero reported SD. That epoch is unidentified. The global datum does not remove disconnected-component null spaces.

**Required correction:** add explicit GLS whitening and covariance shape metadata. Handle reference gauges and connected components explicitly. Return unidentified directions honestly. For bounded parameters, use constrained posterior sampling or justified one-sided intervals. Distinguish conditional curvature from posterior uncertainty.

## SCALE-01: The covariance path needs structural algorithms

**Major for large deployment.** Gibbs sampling builds dense `T×T` matrices. Each iteration performs Cholesky plus generic solves at `uq_bayes.py:299–303`. This costs approximately `O(iterations × T³)` time and `O(T²)` memory. The second-difference precision is banded; dense algebra discards that structure.

One float64 covariance needs roughly 107 MB for 3,650 epochs. At 36,500 epochs, it needs 10.7 GB. Multiple matrices and chains multiply those costs. These are storage calculations, not measured runtime forecasts.

Use banded precision solvers or state-space inference. Represent exponential temporal correlation structurally. Apply common-reference effects as low-rank updates. Retain dense covariances only for small exported subsets. Report cost against epochs, lag samples, configurations, and station pairs.

Shardable execution exists in `bench.py`. However, the reproduction probe accepts duplicate rows with missing shards. Require unique task identifiers, complete expected inventories, configuration hashes, and matching code/data versions before aggregation. Distributed execution is not sufficient evidence of distributed reproducibility.

## Necessary validation before large deployment

1. Separate generator validation from estimator regression tests.
2. Use independent simulator families and multiple paired seeds.
3. Include no-change cases with shared waveform artifacts.
4. Vary source direction, spectra, gaps, clocks, and reference quality.
5. Include overlapping depth kernels and multiple wave types.
6. Measure bias, RMSE, coverage, width, failures, and availability.
7. Report transient amplitude, timing, and trend-slope errors separately.
8. Estimate coverage uncertainty across independent realizations.
9. Test duplicate-pipeline and timestamp-unit invariance.
10. Validate downstream parameter coverage with known synthetic truth.

For nominal 95% coverage, 100 independent realizations give an approximate binomial standard error of 2.2 percentage points. Five hundred give about one point. Correlated epochs cannot replace independent realizations. Predefine acceptable calibration tolerances and failure rates for each scientific use case.

Existing tests are valuable regression evidence. Full test and build outcomes are recorded in [the reproduction audit](evidence/reproducibility.md). They should not be interpreted as uncertainty calibration.
