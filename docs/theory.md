# Theory pointer

The full theoretical framework that `codameter` operationalises is
documented in:

> **Denolle, M. A.** (in prep, submitted to *JGR Solid Earth*).
> Seismic Velocity Changes as Stress and Strain Meters: A Unified Framework
> for Forcing, Coupling, and Inversion.

This page is a roadmap that points from each `codameter` module to the
relevant section of that paper. We do not reproduce derivations here — the
package's job is to let you *run* the framework, not re-derive it.

## Module → manuscript map

| Module | Manuscript section | What it implements |
|---|---|---|
| `forward.thermoelastic` | §3 (thermoelastic) | Berger 1975 / Richter et al. 2014 / Ermert et al. 2023 |
| `forward.poroelastic` | §4.1, §4.2 | Roeloffs 1988, Talwani 2007, Okubo et al. 2024 |
| `forward.loading` | §5 | Tsai 2011 surface load |
| `forward.damage` | §6 | Snieder et al. 2017 logarithmic healing |
| `forward.capillary` | §4.4 | (stub) Shi et al. 2026 dynamic capillary |
| `coupling.tier1_poroelastic` | §9.2 + Fig. 19 | Eq. 15 frequency-dependent β_eff |
| `coupling.tier2_damage` | §9.3 + Fig. 20 | (stub) damage–permeability |
| `coupling.tier3_saturation` | §9.4 + Fig. 21 | (stub) β(S_w) nonlinearity |
| `coupling.tier4_thermo_capillary` | §9.5–9.6 | (stub) SWRC shift |
| `inverse.linear_fit` | §11.6 / Phase 3–4 | Eq. 6 weighted least squares |
| `inverse.coupled_inversion` | Eq. 21 | (stub) state-dependent MCMC, v0.2 |
| `interpretation.stress_at_depth` | §7 + Eq. 7 | bridge relation $\beta = -\mu' \kappa / 2\mu$ |
| `interpretation.water_table` | Eqs. 20–22 | (stub) water-table inversion, v0.2 |

## Key equations in the package

**Eq. 6 — linear superposition (Phase 3 design matrix):**

$$
\frac{\delta v}{v}(t) = a_0 + p_1 \Delta GWL(t) + p_2 T(t - t_{\text{shift}})
+ \sum_i s_i L(t, \tau_{\min}, \tau_{\max}, t_{EQ,i})
$$

**Eq. 7 — bridge relation (Phase 6):**

$$
\beta = -\frac{\mu' \kappa}{2 \mu}
$$

**Eq. 15 — frequency-dependent effective β (Phase 2 Tier 1):**

$$
\beta_{\text{eff}}(\omega) = \beta_{\text{drained}} \cdot
\frac{1 + i \omega/\omega_{\text{drain}} / (1 - \alpha_B B)}{1 + i \omega/\omega_{\text{drain}}}
$$

**Eq. 19 — state-dependent constitutive (v0.2 inversion target):**

$$
\frac{\delta v}{v}(t) = F_{\text{NL}}[\varepsilon(t), S_w(t)]
+ G_{\text{poroelastic}}[\sigma_{\text{eff}}(t), p(t)]
+ R_{\text{damage}}(t)
$$

**Eqs. 20–22 — coupled hydromechanical inversion (v0.2 Phase 6 target):**

water table depth $h(t)$ and saturation $S_w(z, t)$ become
*outputs* of the dv/v analysis, validated against a water-budget model.

## Notation

We follow the manuscript convention. The most common symbols used in
the API:

| Symbol | Meaning | Where |
|---|---|---|
| $\beta$ | acoustoelastic sensitivity to volumetric strain | `material_properties.beta_prior` |
| $\mu'$ | nonlinear-elastic sensitivity to bulk modulus | `material_properties.mu_prime_prior` |
| $\kappa$ | bulk modulus | `Phase1Result.bulk_modulus_pa_at_peak` |
| $\mu$ | shear modulus | `Phase1Result.shear_modulus_pa_at_peak` |
| $B$ | Skempton's coefficient | `material_properties.skempton_B_prior` |
| $\alpha_B$ | Biot's coefficient | `material_properties.biot_alpha_prior` |
| $c$ | hydraulic diffusivity | `material_properties.hydraulic_diffusivity_prior_log10` |
| $\phi$ | porosity | `material_properties.porosity_prior` |
| $\mathrm{Pe}_d$ | drainage Péclet number | `coupling.tier1_poroelastic.drainage_peclet` |
| $L(t)$ | Snieder healing kernel | `forward.damage.snieder_healing` |
