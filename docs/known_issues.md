# Known issues for `dvv-workflow` v0.1

This file documents known limitations and quirks at the v0.1 release.
Each item links to the upstream tracker issue once filed.

---

## Sign convention in `forward/damage.py`

**Severity:** documentation discrepancy — does **not** affect inversion results.

The implementation of `snieder_healing()` in
`src/dvv_workflow/forward/damage.py` returns **positive** values for
`elapsed_s > 0`, while its docstring describes the kernel as
"negative valued, with $L(0) = -\ln(\tau_{\max}/\tau_{\min})$ and $L \to 0$
as $t \to \infty$."

The discrepancy comes from the order of the difference of exponential
integrals:

```python
out[pos] = exp1(t / tau_max_s) - exp1(t / tau_min_s)   # implementation: positive
# vs the docstring's L(t) = -[E1(t/tau_max) - E1(t/tau_min)] = E1(t/tau_min) - E1(t/tau_max)
```

Why it does not affect results: the linear-inversion predictor matrix in
`inverse/linear_fit.py` divides by `L0 = -log(tau_max/tau_min)` (negative),
producing `healing_norm` columns whose sign is consistent with the
synthetic generator that uses the *same* normalisation. The fitted
`s_eq` amplitude therefore recovers the input coseismic drop magnitude
correctly; only the *sign* of `s_eq` relative to the manuscript's
$L(t) < 0$ convention is flipped, which can be confusing when reading
fitted parameter tables next to the paper.

**Fix planned for v0.2:** flip the sign of `out[pos]` in `snieder_healing`
to match the docstring (and thereby match the manuscript convention),
update the `L0` normalisation in `linear_fit.py` accordingly, and update
the synthetic test fixture. The change will not alter the magnitudes of
recovered post-seismic amplitudes; only the sign convention.

The unit test
`tests/test_forward_models.py::TestSniederHealing::test_logarithmic_healing_scales_with_coseismic_amplitude`
documents the current behaviour explicitly so that the fix is caught
when implemented.

---

## Phase 4 coupled inversion — deferred to v0.2

Per the build plan, v0.1 ships only the linear (WLS) inversion. The
state-dependent constitutive form of Eq. 21 (Denolle, in prep) requires
MAP/MCMC handling of nonlinear-in-saturation parameters; this is
scheduled for v0.2 with `emcee` as the backend. A stub
`inverse/coupled_inversion.py` exists today but raises
`NotImplementedError`.

When Phase 2 escalation flags fire in v0.1, the workflow still runs the
linear fit and prints a warning; the user should treat the linear fit
as a baseline and compute coupled corrections by hand (or wait for
v0.2).

---

## Tiers 2, 3, 4 — deferred to v0.3 / v0.4

The Tier 1 poroelastic diagnostic (`drainage_peclet`,
`frequency_dependent_beta_eff`) is fully working. Tiers 2 (damage–
permeability), 3 (saturation-dependent nonlinear elasticity), and 4
(thermo-capillary) have stub modules under `src/dvv_workflow/coupling/`
that document their planned API but do nothing yet. The
`decision_tree.escalation_decision` only inspects Tier 1.

---

## Water-table inversion — deferred to v0.2

Phase 6 currently produces a pressure-sensitivity estimate
$d(\delta v/v)/dp$ and propagates it to a $\mu'$ estimate via the
$\beta$-bridge. The full coupled hydromechanical inversion of
Equations 20–22 (water table depth $h(t)$ and saturation $S_w(z, t)$
as outputs of $\delta v/v$) is scheduled for v0.2; an
`interpretation/water_table.py` stub is present.

---

## `disba` is optional but recommended

The package installs and runs without `disba`; the
`kernels/depth_resolution.py` module falls back to the
$z_{\text{peak}} \approx V_S / (3f)$ rule of thumb (Equation S2 of
Hillers et al. 2015) when `mode='rule_of_thumb'` is used. For
production-quality kernel-weighted depth integrals, install with
`pip install "dvv-workflow[kernels]"` and pass `mode='kernel'` to
`Phase1.run`.

---

## `pyarrow` requirement for the C&D 2023 loader

The Clements & Denolle (2023) Zenodo archive uses Apache Feather as the
on-disk format. `load_clements_denolle_2023` therefore depends on
`pyarrow`, which is a hard dependency of `dvv-workflow`. If you are
in a constrained environment without `pyarrow`, you can convert the
upstream feather files to Parquet once with `pandas`, then point the
loader at the converted directory; the loader auto-detects the
parquet layout (see the docstring).

---

## Half-space layer in `make_fine_model`

`kernels.velocity_models.make_fine_model` discretises the *finite*
layers of a layered Earth model onto a fine grid but preserves the
final (half-space) layer as a single thick entry, to keep the disba
matrix size manageable. If you pass a model whose last layer is
unrealistically thin (i.e., not actually a half-space), you will get
unexpected truncation. Always make the last layer thick (~50 km is
conventional in the example configs).
