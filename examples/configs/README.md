# Example site configurations

This directory holds ready-to-run `Site` configs for the `codameter`
workflow. Each one is a complete YAML contract (location, velocity model,
active forcings, priors, analysis window) that can be loaded with
`load_site(...)` or passed to `codameter run --config <file> --dvv <file>`.

Validate any of them before running:

```bash
codameter validate --config examples/configs/parkfield.yaml
```

## Index

| Config | Site / region | Science goal | Active forcings | Band (Hz) | Window |
|---|---|---|---|---|---|
| [`parkfield.yaml`](parkfield.yaml) | Parkfield HRSN, San Andreas (CA) | Interseismic strike-slip baseline; deviatoric-strain case where the scalar-β fit is *known* to be insufficient, so Phase 5 flags the residual (Okubo et al. 2024; Denolle in prep §10.1) | thermoelastic, hydrological, damage | 0.9–1.2 | 2002–2022 |
| [`cascadia.yaml`](cascadia.yaml) | Northern Cascadia locked zone (WA) | Volumetric-strain case; Tier 1 poroelastic coupling at the drained–undrained transition, large β ≈ 3160 (Denolle in prep §10.2) | hydrological (`roeloffs1988`), loading | 0.4–0.8 | 2005–2024 |
| [`kilauea.yaml`](kilauea.yaml) | Kīlauea summit (HI) | Volcanic forcing-strain anchor; 2018 caldera-collapse stress calibration, radial-fracture β (Denolle in prep §10.3) | thermoelastic, hydrological, damage | 1.0–3.0 | — |
| [`clements_denolle_2023_LJR.yaml`](clements_denolle_2023_LJR.yaml) | CI.LJR, San Gabriel Basin (CA) | Re-run the Clements & Denolle (2023) single-station aquifer-response analysis through the pipeline; type-locality of the 2004–05 winter precipitation response | thermoelastic, hydrological | 2.0–4.0 | — |

## Picking a starting point

- **New site, strike-slip / fault zone** → start from `parkfield.yaml`.
- **Deep, hydrologically driven, isotropic strain** → `cascadia.yaml`.
- **Volcanic / caldera setting** → `kilauea.yaml`.
- **Reproducing Clements & Denolle (2023)** → `clements_denolle_2023_LJR.yaml`
  (see [`examples/02_clements_denolle_2023.py`](../02_clements_denolle_2023.py)).

For the full list of valid forcing-model keys and their hyperparameters,
see the "Models, hyperparameters, and physical bounds" section of the
top-level [`README.md`](../../README.md) or
`codameter.forcing_models` in the source.
