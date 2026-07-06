r"""Use-case -> processing-choice map for dv/v monitoring.

The synthetic engine in :mod:`codameter.synthetic_demo` and the pipeline runner
:func:`codameter.deviations.run_pipeline` operate on a processing-choice set::

    {"estimator", "band", "window", "stack", "reference", "gate"}

but the only baseline shipped so far (``deviations.BASELINE``) is tuned for a
volcano. Different monitoring targets sit at very different frequencies, coda
lapse times and depths: a shallow landslide works at ~4-12 Hz with a sub-second
coda, while a crustal fault works at ~0.1-2 Hz with a 5-30 s coda. This module
turns the per-application recommendations synthesized in
``literature/best_practices.md`` into a machine-readable map:

- :data:`USE_CASES` -- for each application, the recommended ``config`` (a
  ``run_pipeline``-ready choice set), the ``synth`` parameters a matched
  synthetic needs, the name of the ground-truth ``dvv`` generator, and the
  human-facing rationale (ranges, depth note, key rule, citations).
- :func:`recommend` -- return a ``run_pipeline``-ready config for a use case,
  with optional per-axis overrides.
- :data:`ELICITATION` -- the ordered questions the advisor asks a user, plus the
  keyword rules that infer the use case from free-text answers.

This is the single importable source of truth. The golden-dataset generator
(:mod:`codameter.golden`), the tests, and the ``codameter-advisor`` skill all
read from here so the recommendation cannot silently diverge from the survey.
"""
from __future__ import annotations

from copy import deepcopy

# Axis keys of one processing-choice set (mirrors ``deviations.BASELINE``).
CONFIG_KEYS = ("estimator", "band", "window", "stack", "reference", "gate")

# ---------------------------------------------------------------------------
# Per-application recommendations, distilled from literature/best_practices.md.
#
# Each entry:
#   config  : run_pipeline-ready choice set (see CONFIG_KEYS).
#   eps_max : stretching search half-width; must exceed the largest |dv/v| the
#             target reaches, or a stretching/WTS estimate saturates.
#   synth   : synthesis geometry for a *matched* synthetic (fs, maxlag_s,
#             t_coda_s, gen_band). High-frequency, shallow targets need a higher
#             fs and a much shorter coda than the default volcano geometry.
#   dvv     : name of the ground-truth generator (resolved in codameter.golden).
#   ranges / depth_note / key_rule / citations : rationale, for the advisor.
# ---------------------------------------------------------------------------
USE_CASES: dict[str, dict] = {
    "volcano": {
        "config": {
            "estimator": "stretching (TS)",
            "band": (0.4, 1.0),
            "window": (10, 30),
            "stack": 10,
            "reference": "fixed",
            "gate": True,
        },
        "eps_max": 0.06,
        "synth": {"fs": 50.0, "maxlag_s": 50.0, "t_coda_s": 12.0,
                  "gen_band": (0.05, 10.0)},
        "dvv": "volcano",
        "ranges": {
            "band_hz": "~0.1-2 (edifice/deep); 1-4 and >5 for shallow coda",
            "window_s": "~5-35 near-field single-station; up to ~100-120 for pairs",
            "depth": "shallow ~0.3-3 km; occasionally mid-crustal magma ~3-10 km",
        },
        "depth_note": "dv/v dominated by the compliant, crack-rich shallow edifice.",
        "key_rule": ("Environmental (rainfall) correction is essential -- "
                     "hydrological dv/v rivals the pre-eruptive signal (Rivet 2015)."),
        "citations": ["Brenguier2008", "Feng2020", "Donaldson2019", "Rivet2015"],
    },
    "earthquake_fault": {
        "config": {
            "estimator": "stretching (TS)",
            "band": (0.5, 1.5),
            "window": (8, 25),
            "stack": 10,
            "reference": "fixed",
            "gate": True,
        },
        "eps_max": 0.05,
        "synth": {"fs": 50.0, "maxlag_s": 50.0, "t_coda_s": 12.0,
                  "gen_band": (0.05, 10.0)},
        "dvv": "earthquake",
        "ranges": {
            "band_hz": "0.1-2 crustal; 0.06-0.9 mid/deep crust; 4-12 shallow damage",
            "window_s": "~5-30 crustal noise; ~3 for high-freq aftershock autocorr",
            "depth": "coseismic damage shallow (top ~100 m-few km)",
        },
        "depth_note": ("Coseismic reductions are dominantly a shallow (top ~100 m) "
                       "nonlinear site effect; separate it before interpreting fault-zone change."),
        "key_rule": ("Stretching tolerates the coseismic waveform change; use "
                     "wavelet methods when dv/v is large enough to cycle-skip (Mao 2020)."),
        "citations": ["RubinsteinBeroza2005", "Mao2020", "Sheng2022"],
    },
    "landslide": {
        "config": {
            "estimator": "stretching (TS)",
            "band": (4.0, 12.0),
            "window": (0.2, 1.5),
            "stack": 5,
            "reference": "fixed",
            "gate": True,
        },
        "eps_max": 0.09,
        "synth": {"fs": 100.0, "maxlag_s": 8.0, "t_coda_s": 0.6,
                  "gen_band": (1.0, 20.0)},
        "dvv": "landslide",
        "ranges": {
            "band_hz": "~2-20 (clayey precursors cluster 4-12)",
            "window_s": "~0.05-2 (inter-sensor distances of tens of m)",
            "depth": "very shallow, top few m to ~40 m",
        },
        "depth_note": ("Failure surfaces and pore-pressure change are near-surface; "
                       "dv/v reaches several % to +/-10 %."),
        "key_rule": ("Remove the rainfall / freeze-thaw seasonal swing (multi-day "
                     "lag) before reading a pre-failure precursor."),
        "citations": ["Liu2025", "Morimachi2024", "deWit2026"],
    },
    "groundwater": {
        "config": {
            "estimator": "stretching (TS)",
            "band": (2.0, 4.0),
            "window": (2.0, 8.0),
            "stack": 10,
            "reference": "fixed",
            "gate": True,
        },
        "eps_max": 0.03,
        "synth": {"fs": 50.0, "maxlag_s": 20.0, "t_coda_s": 4.0,
                  "gen_band": (0.5, 8.0)},
        "dvv": "groundwater_shallow",
        "ranges": {
            "band_hz": "~2-4 shallow aquifer; ~0.1-2 multi-band for depth",
            "window_s": "~2-8 single-station autocorr; ~15-100 coda-wave",
            "depth": "upper ~50-500 m (high-freq) to ~200-700 m (low-freq multi-band)",
        },
        "depth_note": ("Frequency band selects aquifer depth; a multi-band set "
                       "separates a shallow seasonal from a deep drought trend."),
        "key_rule": ("Fit and remove the thermoelastic component; the hydrologic "
                     "part lags/anticorrelates with precipitation (Clements & Denolle 2023)."),
        "citations": ["ClementsDenolle2023", "Wang2017", "Mao2022"],
    },
    "cryosphere": {
        "config": {
            "estimator": "stretching (TS)",
            "band": (4.0, 14.0),
            "window": (0.3, 0.8),
            "stack": 5,
            "reference": "fixed",
            "gate": True,
        },
        "eps_max": 0.11,
        "synth": {"fs": 100.0, "maxlag_s": 5.0, "t_coda_s": 0.5,
                  "gen_band": (2.0, 25.0)},
        "dvv": "cryosphere",
        "ranges": {
            "band_hz": "~1.5-30 (active layer / rock glacier 4-14); lower for ice sheets",
            "window_s": "~0.3-0.8 for shallow high-freq arrays",
            "depth": "~0-10 m (active layer / firn)",
        },
        "depth_note": "Large seasonal swings (e.g. +3 % to -8 %, James 2019).",
        "key_rule": ("Freeze-thaw drives a large, sharply seasonal dv/v; a fixed "
                     "long reference keeps the seasonal amplitude unbiased."),
        "citations": ["James2019", "Guillemot2021", "Lindner2021"],
    },
    "geothermal": {
        "config": {
            "estimator": "stretching (TS)",
            "band": (0.5, 2.0),
            "window": (10.0, 25.0),
            "stack": 10,
            "reference": "fixed",
            "gate": True,
        },
        "eps_max": 0.03,
        "synth": {"fs": 50.0, "maxlag_s": 40.0, "t_coda_s": 10.0,
                  "gen_band": (0.1, 8.0)},
        "dvv": "geothermal",
        "ranges": {
            "band_hz": "~0.25-3.5 (mining as low as 0.6-1.2)",
            "window_s": "~20 s coda for km-scale reservoirs",
            "depth": "hundreds of m to a few km",
        },
        "depth_note": ("Surface arrays sense the shallow subsurface, not the deep "
                       "plume directly; tie the window to a lapse-time kernel."),
        "key_rule": ("Ambient noise can reveal aseismic reservoir response invisible "
                     "to microseismic monitoring (Obermann 2015)."),
        "citations": ["Obermann2015", "Hillers2015", "Gassenmeier2015"],
    },
}

# Human-readable aliases the advisor maps onto USE_CASES keys.
ALIASES = {
    "fault": "earthquake_fault",
    "earthquake": "earthquake_fault",
    "tectonic": "earthquake_fault",
    "hydrology": "groundwater",
    "aquifer": "groundwater",
    "permafrost": "cryosphere",
    "glacier": "cryosphere",
    "glacial": "cryosphere",
    "reservoir": "geothermal",
    "co2": "geothermal",
    "mining": "geothermal",
}


def resolve(use_case: str) -> str:
    """Normalize a free-text use-case label to a :data:`USE_CASES` key."""
    key = use_case.strip().lower().replace(" ", "_").replace("/", "_")
    if key in USE_CASES:
        return key
    if key in ALIASES:
        return ALIASES[key]
    # Fall back to a keyword scan over the raw text.
    text = use_case.lower()
    for word, target in ALIASES.items():
        if word in text:
            return target
    for ck in USE_CASES:
        if ck.split("_")[0] in text:
            return ck
    raise KeyError(
        f"unknown use case {use_case!r}; known: {sorted(USE_CASES)} "
        f"(aliases: {sorted(ALIASES)})"
    )


def recommend(use_case: str, **overrides) -> dict:
    """Return a ``run_pipeline``-ready config for ``use_case``.

    ``overrides`` replace individual axes (any of :data:`CONFIG_KEYS`), e.g.
    ``recommend("volcano", band=(0.2, 0.5))`` to try a lower band. Unknown
    override keys raise, so a typo cannot silently pass through.
    """
    key = resolve(use_case)
    cfg = deepcopy(USE_CASES[key]["config"])
    bad = set(overrides) - set(CONFIG_KEYS)
    if bad:
        raise KeyError(f"unknown config axes {sorted(bad)}; valid: {CONFIG_KEYS}")
    cfg.update(overrides)
    return cfg


def synth_params(use_case: str) -> dict:
    """Synthesis geometry (fs, maxlag_s, t_coda_s, gen_band) for a matched synthetic."""
    return deepcopy(USE_CASES[resolve(use_case)]["synth"])


def eps_max(use_case: str) -> float:
    """Stretching search half-width matched to the target's dv/v amplitude."""
    return float(USE_CASES[resolve(use_case)]["eps_max"])


# ---------------------------------------------------------------------------
# Elicitation: what the advisor asks, and how free-text answers map to a
# use case and to per-axis overrides.
# ---------------------------------------------------------------------------
ELICITATION = [
    {
        "id": "application",
        "question": "What are you monitoring?",
        "why": "Sets the whole parameter regime (band, coda window, depth).",
        "options": [
            "Volcano", "Earthquake / fault", "Landslide",
            "Groundwater / aquifer", "Cryosphere (permafrost / glacier)",
            "Geothermal / reservoir / CO2 / mining",
        ],
        "maps_to": "use_case",
    },
    {
        "id": "target_process",
        "question": "What physical change are you trying to detect?",
        "why": "Distinguishes a transient (eruption, coseismic step, pre-failure) "
               "from a slow trend or a seasonal cycle -- this sets stack length "
               "and reference scheme.",
        "options": ["A transient event", "A slow multi-year trend",
                    "A seasonal cycle", "Not sure"],
        "maps_to": "stack_and_reference",
    },
    {
        "id": "frequency",
        "question": "What frequency content dominates your correlations (Hz)?",
        "why": "Frequency band selects the sensing depth; override the default "
               "band if the user names a specific range.",
        "options": ["<1", "1-4", "4-12", ">12", "Not sure"],
        "maps_to": "band",
    },
    {
        "id": "geometry",
        "question": "What is your station geometry?",
        "why": "Single-station autocorrelation vs station pairs vs dense array "
               "sets the minimum usable lapse and the aggregation scheme.",
        "options": ["Single station (autocorr / cross-comp)",
                    "Station pairs", "Dense array"],
        "maps_to": "aggregation",
    },
    {
        "id": "amplitude",
        "question": "How large a dv/v do you expect?",
        "why": "Large dv/v (> ~1 %) can cycle-skip cross-spectral methods and "
               "must widen the stretching search (eps_max).",
        "options": ["Small (< 0.1 %)", "Moderate (0.1-1 %)",
                    "Large (> 1 %)", "Not sure"],
        "maps_to": "estimator_and_eps",
    },
    {
        "id": "cadence",
        "question": "What temporal resolution do you need?",
        "why": "Daily/transient resolution wants a short stack; a long trend "
               "tolerates a longer stack for lower noise.",
        "options": ["Daily", "Weekly", "Monthly / seasonal"],
        "maps_to": "stack",
    },
    {
        "id": "noise",
        "question": "Any known data problems?",
        "why": "Clock error, non-stationary noise sources and low SNR each map "
               "to a specific safeguard (branch check, band restriction, gating).",
        "options": ["Clock / timing errors", "Non-stationary noise sources",
                    "Low SNR", "Gaps in the record", "None known"],
        "maps_to": "safeguards",
    },
]
