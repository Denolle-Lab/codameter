# Advisor and golden-dataset audit

The advisor has a useful design principle: execute recommendations. Its central configuration map prevents silent value drift. The documentation also acknowledges synthetic-to-field limitations. However, its current examples, scorer, and validation evidence do not support a claim of robust agent evaluation.

This audit inspected the advisor as an artifact. It did not invoke it for operational recommendations. No external model benchmark or private corpus was accessed.

## AG-01: The six-application validation example is incomplete

**Major.** The skill promises six application families. Its standard validation calls `MAINSTREAM_BY_USE_CASE[key]`. The public checkout contains only three cases:

| Application | Public validation route |
|---|---|
| Volcano | `easy-volcano-01` |
| Earthquake/fault | `medium-earthquake_fault-02` |
| Groundwater | `hard-groundwater-04` |
| Landslide | `KeyError` |
| Cryosphere | `KeyError` |
| Geothermal | `KeyError` |

See `golden.py:317–365` and advisor `references/validation_loop.md:37–46`. A fallback to `generate` cannot create an unregistered recipe. The advisor needs public development cases for every supported route.

The groundwater fallback is also a deep-targeted hard case. Its manifest overrides the band to `0.55–1.2 Hz`. The example instead uses the generic recommendation, `2–4 Hz`. It runs on averaged CCFs, although `golden.recover` measures channels separately before averaging. The advisor therefore does not reproduce the benchmark's target or aggregation protocol.

**Fix:** provide explicit public development recipes per application. Respect case-level target metadata and use `golden.recover`. Distinguish a broad application default from a site-specific recommendation. Add executable smoke checks for every documented route.

## AG-02: Recommendation quality is not evaluated directly

**Major.** The skill elicits geometry, cadence, amplitude, and noise conditions. Most are descriptive mappings for the language model. The config contains only six axes. It omits timing checks, aggregation, explicit reference dates, and search-width provenance.

The standard example fixes `eps_max` by application. It does not propagate a user's amplitude answer. `recommend` checks unknown keys but does not fully validate values. Invalid bands, windows, durations, and unsupported combinations need explicit checks.

The example reports one realization's RMS and valid count. It supplies neither repeated-seed uncertainty nor a measured error-bar comparison. Calling choices equivalent within 20% RMS is a heuristic, not an equivalence test. See `validation_loop.md:45–53`.

**Fix:** record elicited constraints and resulting overrides. Add tests for conflicting inputs, missing information, abstention, search saturation, and unavailable bands. Compare paired-seed differences with uncertainty. Specify scientifically meaningful equivalence margins beforehand.

## AG-03: Synthetic ranking does not prove field suitability

**Major.** The skill description says the synthetic engine “proves” the recommendation. Its governance section correctly limits the claim. These instructions conflict.

The application recommendation and simulator geometry share `use_cases.py`. Hard cases generate two separated frequency bands and explicitly identify them as layers. This validates spectral selection under a designed signal separation. It does not validate depth resolution in a scattering Earth.

See `golden.py:190–213,381–445`. Real depth sensitivity can overlap across frequencies and depend on wave type, lapse time, velocity structure, and scattering. An empirical field claim needs independent observations or controlled signal injection into measured CCFs.

**Fix:** describe results as conditional synthetic checks. Require field-data diagnostics before claiming site suitability. Test smooth overlapping kernels, mixed wavefields, seasonal source changes, and common artifacts. Compare against a fixed literature default and exhaustive configuration search. Measure recommendation regret on held-out scenarios.

## EV-01: Missing predictions can earn perfect scores

**Submission blocker for evaluation claims.** `frugalmind.score_dvv_series:299–307` marks finite predictions as valid. `golden._rms:578–596` requires only ten valid epochs. It evaluates only those epochs and chooses its baseline from them.

The probe submits valid JSON: ten zeros followed by `null`. NumPy converts the null entries to missing values. Results:

| Public case | Full zero-series score | Ten zeros, remaining values missing |
|---|---:|---:|
| Easy volcano, 1,095 days | 0.0 | **1.0** |
| Medium fault, 1,095 days | 0.0 | **1.0** |
| Hard groundwater, 913 days | 0.0 | **1.0** |

The submission observes no waveform and estimates under 1.1% of dates. This is a scorer defect, not evidence that any evaluated model exploited it. The parameter scorer also evaluates a pipeline's own valid mask. It needs availability safeguards too.

**Fix:** define the scoring support independently of model output. Require finite predictions where the task requires daily estimates. If abstention is allowed, score availability and scientific error jointly. Fix baseline epochs beforehand. Add adversarial tests for nulls, NaNs, selective event omission, and sparse constants. Re-score any existing results after fixing the scorer.

## EV-02: Truth stripping is not an isolation boundary

**Major deployment requirement; no private leak demonstrated.** `golden.observed` removes truth keys, but calls `generate` in the same module. The series prompt directs the agent to import that module. In a process with private recipes available, the agent could call `generate` directly or inspect `CASES_BY_ID`.

The private-dataset documentation recognizes this risk. It requires scorer credentials and recipes outside the agent sandbox. That isolation is a requirement, not an implemented guarantee demonstrated by the repository's key-removal test.

Exported rows also contain `metadata.recommended_config`, at `frugalmind.py:193–196`. This can remain useful scorer metadata. It must not enter agent-visible context. Public cases are explicitly reconstructible and cannot establish hidden generalization.

**Fix:** materialize observables in a separate preparation process. Give the agent an artifact identifier and a truth-free reader. Keep recipes, secrets, scorer thresholds, and recommended configurations outside its environment. Test this boundary with an adversarial filesystem/API audit. Record precisely what the agent can access.

## EV-03: A regression corpus is not an independent gold standard

**Major.** The generator defines 30 templates. The public manifest contains three cases. Default private generation excludes those three, leaving 27. Documentation variously describes 30 cases and ten cases per suite. See `private_golden.py:85–91`, advisor `references/golden_datasets.md:3–5`, and integration README lines 19–22.

The hidden set randomizes amplitudes, phases, and event timing. It retains generator families, physical sign patterns, synthesis geometry, and difficulty recipes. This is useful parameter holdout. It does not establish simulator-family or field-domain generalization.

Easy and medium cases are validation; hard cases are test. Difficulty and split are therefore confounded. A benchmark should report within-regime holdout separately from harder-domain transfer.

The oracle is the recommended implementation's RMS. Tolerances range from 35% to 60%. These are broad regression drift guards. They are not scientific accuracy criteria. Regenerating expected metrics alongside code changes can normalize a regression unless independent acceptance limits are retained.

**Fix:** freeze a release-specific benchmark before evaluating models. Hash recipes, observable arrays, truth, scoring code, and thresholds. Use separate development, calibration, and locked test corpora. Hold out source/noise/kernel families as well as parameters. Report paired uncertainty intervals across cases and seeds.

## EV-04: No executed agent evaluation supports the abstract

**Major evidence gap.** The reviewed tree provides skill instructions, export adapters, and deterministic scorer tests. It does not provide a model-result table, execution transcripts, prompt/version hashes, or repeated agent runs supporting the abstract's robust-evaluation claim.

`tests/test_frugalmind_export.py` checks schema and scorer behavior. It does not evaluate elicitation, citation grounding, tool use, reasoning, uncertainty reporting, or adherence to user constraints. A passing scorer test cannot establish advisor reliability.

**Fix:** run and archive a real evaluation after scorer repair. Compare:

1. A fixed application-default lookup.
2. A random feasible configuration baseline.
3. Exhaustive or budget-matched configuration search.
4. The same model without the advisor skill.
5. The model with the advisor skill.

Report recovery, availability, failures, constraint adherence, calibration, latency, and cost. Include uncertainty across repeated runs. Keep assessment of physical measurement separate from conversational correctness.

## Minimum evaluation record

| Field | Required content |
|---|---|
| Dataset identity | Version, split, hashes, generator family |
| Execution identity | Code SHA, dependencies, hardware, precision |
| Advisor identity | Skill hash, reference hashes, prompt hash |
| Model identity | Provider identifier, settings, date |
| Tool access | Allowed files/APIs and denied truth access |
| Output | Full response, config, series, masks, errors |
| Score | Metric version, fixed support, component scores |
| Repetition | Scenario seed and agent-run index |
| Failures | Exceptions, timeout, abstention, missing predictions |

The project can support a useful advisor benchmark. Its strongest current evidence is executable infrastructure. Scientific generalization and agent reliability remain to be demonstrated.
