# Forward models

## Thermoelastic

::: codameter.forward.thermoelastic
    options:
      show_root_heading: false
      members:
        - thermal_skin_depth
        - berger_temperature_response
        - fourier_temperature_decomposition
        - thermoelastic_dvv

## Poroelastic

::: codameter.forward.poroelastic
    options:
      show_root_heading: false
      members:
        - roeloffs_pressure_response
        - drained_pressure_response
        - talwani_precipitation_response
        - groundwater_level_okubo

## Damage / healing

::: codameter.forward.damage
    options:
      show_root_heading: false
      members:
        - snieder_healing
        - logarithmic_healing
