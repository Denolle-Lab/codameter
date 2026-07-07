# Use case to config map

The authoritative map is `codameter.use_cases.USE_CASES`, distilled from
`literature/best_practices.md`. Do not restate parameter values from memory; read
them from the module so the recommendation cannot drift from the survey.

```bash
pixi run python -c "
import json
from codameter import use_cases as uc
key = uc.resolve('volcano')
e = uc.USE_CASES[key]
print('config ', uc.recommend(key))
print('eps_max', uc.eps_max(key))
print('ranges ', json.dumps(e['ranges']))
print('depth  ', e['depth_note'])
print('rule   ', e['key_rule'])
print('cites  ', e['citations'])"
```

## The six use cases (summary)

Read the live values before quoting; this table is orientation only.

| Use case | Band (Hz) | Coda window (s) | Depth | What dominates the choice |
| --- | --- | --- | --- | --- |
| volcano | ~0.4-1 (0.1-2 regime) | 10-30 | shallow edifice ~0.3-3 km | band vs depth; rainfall correction |
| earthquake_fault | ~0.5-1.5 (0.1-2 crustal) | 8-25 | shallow damage top ~100 m-km | separate shallow site effect |
| landslide | ~4-12 (2-20) | 0.2-1.5 | very shallow, m to ~40 m | high freq, sub-second coda, large dv/v |
| groundwater | ~2-4 (0.1-2 multiband) | 2-8 | ~50-500 m | band selects aquifer depth |
| cryosphere | ~4-14 (1.5-30) | 0.3-0.8 | ~0-10 m active layer | large sharp seasonal swing |
| geothermal | ~0.5-2 (0.25-3.5) | 10-25 | hundreds of m to km | low band for depth penetration |

## Cross-cutting rules (apply to every use case)

From `literature/best_practices.md`, section "Cross-cutting methodology rules":

- Later coda amplifies small dv/v but has lower SNR; the window trades sensitivity
  against noise.
- Stretching is the robust default at low SNR and large dv/v; cross-spectral
  methods (MWCS, WCS) cycle-skip at large dv/v; wavelet and DTW help at low SNR.
- Quantify uncertainty explicitly (coherence-weighted phase error for MWCS, the
  Weaver/Clarke RMS bound for stretching). Keep `gate=True`.
- Depth is set by band and coda lapse, not assumed. Do not reuse one coda window
  across frequency bands (see the freqdep golden case).
- A long, stable reference and a consistent stacking scheme keep the long-term
  trend and seasonal amplitude unbiased. A `moving` reference erases slow trends;
  use `fixed` or `inversion` for a trend.
- Beware spurious dv/v from non-stationary noise sources; restrict to stable
  bands and verify spectral stationarity.

## Applying overrides

If the user pinned an axis (for example "I have to use 1-2 Hz"), pass it as an
override and keep the rest of the recommendation:

```bash
pixi run python -c "from codameter import use_cases as uc; print(uc.recommend('volcano', band=(1.0,2.0)))"
```

`recommend` rejects unknown axes, so a typo fails loudly rather than passing
through silently.
