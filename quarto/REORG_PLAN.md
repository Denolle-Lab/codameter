# Uncertainty-narrative reorganization — session handoff

> Status: **planned, not started.** This document is the full context for a
> future session to reorganize the `codameter` narrative site's uncertainty
> story into a clean forward-propagation arc:
> **measurement error → depth → stress/strain at depth.**
> Written 2026-06-26. Author of current state: prior Claude session.

---

## 0. The goal (Marine's proposed flow)

Reorder the uncertainty pages so the reader follows the physical propagation of
error:

1. **Errors in the measurement** (the $\delta v/v$ value itself).
2. **Propagated errors with depth** (frequency-band errors → a depth profile).
3. **Propagated errors to the stress/strain estimate at depth.**

This is the correct dependency order — each step consumes the previous step's
*covariance*. Adopt it as the spine. See §3 for the critique that shapes the
target design.

---

## 1. Current state (inventory)

### Narrative pages (`quarto/*.qmd`)
All render live against the installed `codameter` package via the
`codameter-pixi` Jupyter kernel; execution is frozen in `quarto/_freeze/`.

| Page | Role today | Section headers |
|---|---|---|
| `index.qmd` | Landing; "two theoretical contributions" + tutorial map | — |
| `theory-uq.qmd` | **Inference UQ** — epistemic, Bayesian stress *inversion* | 1 Why point estimates fail · 2 Likelihood (+ "diagonal $C_d$ is an assumption" callout) · 3 Decoupled/coupled regimes · 4 Coupling as Bayesian model selection · 5 Physics priors · 6 **Propagating to stress** (bridge chain, delta/MC) · 7 Posterior predictive checks · 8 Summary diagram |
| `theory-measurement-uq.qmd` | **Measurement UQ** — aleatoric error in $\delta v/v$ | 1 Tree of choices · 2 Within-method floor (Weaver/Clarke) · 3 Methodological ensemble · 4 Temporal + common-mode correlation · 5 Reference / Brenguier all-to-all · 6 $C_d$ into GLS · 7 Full-budget diagram |
| `theory-processing-depth.qmd` | **Processing → depth** | 1 Window rule is freq-dependent · 2 Sampling the multiverse + per-band error · 3 One error per band → kernel · 4 Depth inversion propagation · 5 Full-chain diagram |
| `tutorial-01..06` | The implementation tutorial (Phases 0–6) | (unchanged by this reorg) |

### Source modules (`src/codameter/`)
| Module | Public API (exported in `__init__.py`) | Purpose |
|---|---|---|
| `uq_measurement.py` | `weaver_stretching_error`, `processing_ensemble`/`EnsembleResult`, `temporal_error_covariance`, `effective_sample_size`, `global_reference_inversion`/`GlobalReferenceSolution`, `single_reference_dvv` | Error-model primitives: floor, ensemble, structured $C_d$, Brenguier inversion |
| `uq_processing.py` | `ProcessingPrior`, `ProcessingChoice`, `sample_processing_choices`, `per_band_marginal_error` (+ `flatten_end_lapse`, `choice_floor`, `WINDOW_RULES`) | Processing choices as Bayesian nuisance params; window rules (fixed / envelope-pick-flatten / moving); marginalize → one error per band |
| `uq_depth.py` | `band_sensitivity_matrix`/`DepthKernels`, `invert_depth_profile`/`DepthProfilePosterior` | Frequency→depth: Rayleigh kernels $G(f,z)$ from disba; Bayesian linear inversion (stable GP/Woodbury form) → $\delta V_S/V_S(z)$ posterior |
| `interpretation/stress_at_depth.py` | (existing, pre-UQ work) | **Time-domain** stress: takes the fitted hydrological coefficient $p_1$ at the **peak depth**, applies bridge relation $\beta=-\mu'\kappa/2\mu$. NOT depth-resolved. |
| `uq-measurement.py` (hyphen!) | not importable | Marine's earlier **coda-window design scorer** (CodaWindow, scoring). Different concern (which window to pick), left intact. Do NOT confuse with `uq_measurement.py`. |

### Tests (all pass: 137 passed, 1 skipped)
`tests/test_uq_measurement.py` (7), `tests/test_uq_processing.py` (4),
`tests/test_uq_depth.py` (5, skipped if disba absent).

### Nav (`quarto/_quarto.yml`)
`Theory` navbar menu and the "Theoretical contributions" sidebar section both
list, in order: `theory-uq` → `theory-measurement-uq` → `theory-processing-depth`.

---

## 2. The overlap to fix

`theory-measurement-uq` §1–5 **and** `theory-processing-depth` §1–2 both cover
"error in the measurement" (floor, processing-choice sampling, ensemble). This
is redundant and splits one idea across two pages. The reorg collapses them.

---

## 3. Critique of the proposed flow (decisions baked into the target)

1. **Aleatoric vs epistemic must both appear at step 3.** Steps 1–2 are the
   *aleatoric* forward chain. The *dominant* stress uncertainty is *epistemic*
   (priors on $\beta,\mu',\kappa$; coupling model-form) — see `theory-uq` §1.
   **Step 3 must merge the forward depth-covariance with the material-property
   prior covariance**, or it understates stress uncertainty badly.

2. **Time vs depth — name the data cube.** Measurement error is in *time*
   ($\delta v/v(t)$, temporal $C_d$, reference choice). Depth inversion is in
   *frequency* (bands). The honest object is $\delta v/v(f,t)$ inverted for
   $m(z,t)$. Current pages each show a 1-D slice silently. The reorg should
   state the cube and label which slice each page uses.

3. **Step 2→3 representation mismatch (this is real new work).** Step 2 outputs
   a $\delta V_S/V_S(z)$ *profile*; the existing `stress_at_depth` works from a
   *time-domain coefficient at one depth*. **Depth-resolved stress from a
   profile does not exist yet** — it is the new module step 3 needs.

4. **`theory-uq` is broader than "propagate to stress."** It is the whole
   time-domain forcing inversion + coupling model selection. Keep it as a
   companion "Inference UQ" axis; refocus only its §6 to hand off to the new
   step-3 page.

---

## 4. Target structure — a 3-page "Uncertainty" pillar (theory-uq FOLDED IN)

**Decision (Marine, 2026-06-26):** `theory-uq` is **folded into page 3**, not
kept as a separate pillar. The arc is exactly the three forward steps.

| # | Page (proposed file) | Built from | Output object |
|---|---|---|---|
| overview (optional) | `uncertainty-overview.qmd` | merge the "full budget" mermaid diagrams | the map: aleatoric chain ⟂ epistemic priors |
| 1 | `uncertainty-1-measurement.qmd` | `theory-measurement-uq` §1–6 **+** `theory-processing-depth` §1–2 | structured $C_d$ (per-time and per-band) |
| 2 | `uncertainty-2-depth.qmd` | `theory-processing-depth` §3–5 | $\delta V_S/V_S(z)$ posterior $C_m(z)$, resolution |
| 3 | `uncertainty-3-stress.qmd` **(NEW code + folds `theory-uq`)** | new `uq_stress_depth` module **+ all of `theory-uq` §3–7** (regimes, coupling model-selection, physics priors, propagation, predictive checks) recast in the depth-resolved stress context | **strain$(z)$, effective stress$(z)$, total stress$(z)$** posteriors, full (aleatoric ⊕ epistemic) budget |

`theory-uq.qmd` is **deleted** after migration; its §2 "diagonal $C_d$" idea is
already pointed at page 1, and its unique time-domain forcing/coupling material
either moves into page 3's "model-form uncertainty" section or links down to the
tutorial (`tutorial-03/04/05` already cover inversion/coupling/interpretation).

Nav labels: "1 · Measurement", "2 · Depth", "3 · Stress, effective stress &
strain".

---

## 5. New code required for step 3 (`uq_stress_depth.py`)

The missing capability: turn a $\delta V_S/V_S(z)$ **posterior profile** (from
`uq_depth.invert_depth_profile`) into **strain, effective stress, AND total
stress profiles** with a combined covariance.

**Decision (Marine, 2026-06-26):**
- $\beta(z), \mu'(z)$ are **layered (depth-dependent)**, and "**sometimes
  inferred from tomography models (Vp, Vs)**". So the module takes *per-layer*
  priors, optionally generated from the velocity model via a supplied
  $\beta,\mu'(V_P,V_S)$ mapping (lithology/Vs-scaling/lookup) — NOT a single
  scalar prior.
- Headline output is **stress**, but the module must also extract
  **effective stress** and **strain**. Effective stress is the
  poroelastically-correct quantity ($\sigma' = \sigma - \alpha_B p$); reuse the
  existing `MaterialProperties` Biot $\alpha_B$ and Skempton $B$ priors.

Physics (per depth $z$):
- Acoustoelastic (volumetric strain): $\varepsilon_{\rm vol}(z) =
  (\delta V_S/V_S)(z)/\beta(z)$.
- Bridge relation (nonlinear elasticity): $\beta(z) = -\mu'(z)\,\kappa(z)/2\mu(z)$.
- Moduli from the (tomography) velocity model:
  $\mu(z)=\rho(z)V_S(z)^2$, $\kappa(z)=\rho(z)(V_P^2-\tfrac43 V_S^2)$ — from
  `VelocityProfile`.
- **Effective stress:** $\Delta\sigma'(z) = \kappa(z)\,\varepsilon_{\rm vol}(z)$
  (drained), the quantity $\delta v/v$ most directly senses.
- **Total stress:** $\Delta\sigma(z) = \Delta\sigma'(z) + \alpha_B(z)\,\Delta p(z)$
  (Biot); needs a pore-pressure term (from the hydrological forcing / Phase 6).

Proposed API:
```python
@dataclass
class StressDepthPosterior:
    depths_km
    strain_mean, strain_cov
    eff_stress_mean, eff_stress_cov      # effective stress σ'(z)
    stress_mean, stress_cov              # total stress σ(z)

def moduli_profile(profile: VelocityProfile) -> dict   # mu(z), kappa(z), rho(z)

def layered_acoustoelastic_priors(           # β(z), μ'(z) from tomography
    profile: VelocityProfile, mapping=...,   # e.g. β = f(Vs), per-lithology
) -> dict                                    # {beta:(mean(z),std(z)), mu_prime:(...)}

def stress_profile_from_dvv(
    depth_post: DepthProfilePosterior,       # aleatoric C_m(z) from step 2
    profile: VelocityProfile,
    beta_zprior, mu_prime_zprior,            # LAYERED epistemic priors (z-arrays)
    *, pore_pressure=None, biot_alpha_prior=None,  # for total stress
    n_mc: int = 20000, rng=...,
) -> StressDepthPosterior:
    # Monte-Carlo pushforward: draw m(z) ~ N(depth_post.mean, depth_post.cov)
    # AND per-layer beta(z), mu'(z), moduli, alpha_B ~ priors; evaluate
    # strain → effective stress → total stress per draw; report mean + cov.
    # (MC because the maps are ratios/products; delta-method is the linear
    # fallback — mirror theory-uq §6, which is being FOLDED into this page.)
```
This is the depth-resolved analogue of the existing scalar `stress_at_depth`.
Reuse the MC-pushforward pattern from `tutorial-05-interpretation.qmd` (fig-mc)
and `theory-uq` §6. The **epistemic** material priors entering here are what make
the stress uncertainty honest — this is the merge point of the two budgets.

Tests to add (`tests/test_uq_stress_depth.py`): moduli from a known profile;
layered β/μ′ generation; MC reproduces delta-method in the small-σ limit;
effective-stress and total-stress covariances ⪰ the aleatoric-only covariance
(priors add variance); total stress reduces to effective stress when
$\alpha_B\to0$ or $\Delta p\to0$; shape guards.

---

## 6. Migration map (mechanical)

1. **Create page 1** `uncertainty-1-measurement.qmd`: paste `theory-measurement-uq`
   §1–6, then insert `theory-processing-depth` §1–2 (window rules + multiverse
   sampling + per-band error) as new subsections between "within-method floor"
   and "methodological ensemble". One setup cell importing from both
   `uq_measurement` and `uq_processing`.
2. **Create page 2** `uncertainty-2-depth.qmd`: `theory-processing-depth` §3–5,
   with a one-paragraph recap that the per-band $\sigma_b$ came from page 1.
3. **Create page 3** `uncertainty-3-stress.qmd` — write against the new
   `uq_stress_depth` module AND **fold in `theory-uq` §3–7**: the
   decoupled/coupled regimes, coupling-as-model-selection, physics priors,
   the propagation-to-stress (bridge) section, and posterior predictive checks —
   all recast for depth-resolved strain / effective stress / total stress. Pull
   the MC-pushforward figure idea from `tutorial-05`. This page is the merge
   point of the aleatoric depth covariance and the epistemic material priors.
4. **Delete `theory-uq.qmd`** once §3–7 are folded into page 3. Its §1–2 framing
   (point-estimates-are-not-enough, the diagonal-$C_d$ callout) becomes the
   intro of page 3 / the overview; its time-domain forcing-decomposition angle,
   if not needed in page 3, links down to `tutorial-03/04/05`.
5. **Delete** `theory-measurement-uq.qmd` and `theory-processing-depth.qmd`
   after content is migrated (Quarto has no native redirect; delete and fix
   inbound links).
6. **Fix all cross-links**: search `grep -rl "theory-measurement-uq\|theory-processing-depth" quarto/*.qmd` and repoint to the new files. Also `index.qmd` (the "two contributions" block → "the uncertainty arc, in N steps").
7. **Update `_quarto.yml`**: replace the three Theory entries with the
   overview + 4-page ordered list (navbar menu AND sidebar section).
8. **Render & deploy** (see §7).

Estimated effort: ~1 focused session. Steps 1–2,4,6–8 are mechanical
(cut/paste/relink). Step 3 + the new module is the only real authoring/coding.

---

## 7. Build & deploy mechanics (must-know)

- **Render:** `export QUARTO_PYTHON=$PWD/.pixi/envs/default/bin/python && pixi run quarto render quarto/`
- **Kernel gotcha:** every executable page needs `jupyter: codameter-pixi` in
  its front matter. The machine's default `python3` kernel is an unrelated
  `quakellm` env without `codameter`. Re-register if missing:
  `pixi run python -m ipykernel install --user --name codameter-pixi --display-name "codameter (pixi)"`.
- **Freeze:** executed outputs are cached in `quarto/_freeze/` and committed; CI
  does NOT render (it publishes the committed `quarto/_site/`). After any `.qmd`
  edit, re-render locally and commit `quarto/_site` + `quarto/_freeze`.
- **Deploy:** push to `master` → `.github/workflows/quarto.yml` publishes
  `quarto/_site` to `gh-pages` (peaceiris). Live at
  https://denolle-lab.github.io/codameter/ . First load of a new page can 404
  for ~1 min (Pages CDN lag).
- **disba:** required for `uq_depth` kernels; installed in the pixi env. Bands
  must stay where sensitivity is within the resolved model (~0.6–4.5 Hz, peaks
  ~30–470 m for the Parkfield synthetic) or low-f kernels leak into the
  half-space. Use `max_depth_km` to truncate.
- **Numerical landmine (already fixed, don't reintroduce):** in
  `uq_depth.invert_depth_profile`, do NOT invert the smooth prior covariance
  `Cm0` directly — it is near-singular on a fine grid and the posterior std then
  violates monotonicity. Use the GP/Woodbury form (invert only the
  $n_{\rm band}\times n_{\rm band}$ data-space matrix). The new
  `uq_stress_depth` MC pushforward avoids this entirely.

## 8. Gotchas & repo facts

- **CI is not gated on `master`.** `ci.yml` (ruff/black/pytest) and `docs.yml`
  (mkdocs) trigger on `main`/`dev` only; the default branch is `master`. So
  pre-existing lint errors exist in other files and nothing auto-checks pushes.
  Keep new files clean manually: `pixi run --environment dev ruff check <files>`
  and `black <files>`; run `pixi run --environment test pytest -q`.
- **mkdocs vs quarto** both target `gh-pages`; mkdocs only deploys on `main`
  (inactive on `master`), so the quarto site currently owns Pages. Keep one
  source of truth.
- The hyphen file `src/codameter/uq-measurement.py` is Marine's window-DESIGN
  scorer (not importable, intentionally separate). Offer to rename to
  `uq_window_design.py` and reconcile, but do not silently overwrite.
- House plotting style + synthetic data live in `quarto/_synth.py`
  (`set_style`, `C` color dict, `make_synthetic`, `build_parkfield_site`).

## 9. Design questions — RESOLVED (Marine, 2026-06-26) except #1

2. ✅ **Depth-dependent priors:** $\beta(z),\mu'(z)$ are **layered**, sometimes
   **inferred from tomography (Vp, Vs)**. → `uq_stress_depth` takes per-layer
   priors, optionally generated from the velocity model via a
   $\beta,\mu'(V_P,V_S)$ mapping. (See §5.)
3. ✅ **Output:** headline is **stress**, but also extract **effective stress**
   and **strain**. → all three on the `StressDepthPosterior`; effective stress is
   the poroelastic $\sigma'=\sigma-\alpha_B p$ form. (See §5.)
4. ✅ **Fate of `theory-uq`:** **fold into page 3** and delete it. (See §4, §6.)

1. ⏳ **STILL OPEN — depth × time cube:** invert a per-time snapshot for
   $m(z,t)$, or fit time-domain forcing coefficients *per band* (reusing the
   existing Phase 3/4 inversion) and then invert those band-coefficients over
   depth? **Recommended default** (so the next session isn't blocked): the
   latter — fit per-band forcing sensitivities in time (reuses existing
   machinery), then push those + their covariance through `uq_depth` and
   `uq_stress_depth`. This yields a depth profile of the *stress sensitivity*
   with a full budget. Confirm with Marine before building page 3.
