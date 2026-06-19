"""
Forcing-model registry: the canonical names (and accepted aliases) for the
forward model attached to each forcing channel.

This is the single source of truth for *which* model strings are valid in a
:class:`~codameter.config.ForcingSpec`. ``Site`` construction validates
``forcings.<channel>.model`` against this registry, and the design-matrix
builder normalises aliases to their canonical name before dispatching.

Each channel maps a canonical model name to the set of accepted aliases::

    FORCING_MODELS["hydrological"] = {
        "baseflow": {"okubo_gwl", "okubo2024"},
        "drained":  {"roeloffs1988"},
        ...
    }

Use :func:`valid_models` to list the canonical options for a channel and
:func:`canonical_model` to resolve a user-supplied string (canonical or
alias) to its canonical form, raising a helpful error otherwise.
"""
from __future__ import annotations

# channel -> {canonical_name: {accepted aliases}}
FORCING_MODELS: dict[str, dict[str, frozenset[str]]] = {
    "thermoelastic": {
        "berger": frozenset({"phase_shift", "berger1975"}),
    },
    "hydrological": {
        "baseflow": frozenset({"okubo_gwl", "okubo2024"}),
        "talwani": frozenset(),
        "drained": frozenset({"roeloffs1988"}),
        "cdm": frozenset(),
        "precomputed": frozenset(),
    },
    "capillary": {
        "vahedifard": frozenset({"shi2026"}),
    },
    "loading": {
        "instantaneous": frozenset(),
        "snowpack": frozenset(),
    },
    "damage": {
        "snieder_healing": frozenset({"snieder2017"}),
        "logarithmic_healing": frozenset({"logarithmic"}),
    },
}

# channel -> {accepted string (canonical or alias): canonical name}
_ALIAS_TO_CANONICAL: dict[str, dict[str, str]] = {
    channel: {
        **{canonical: canonical for canonical in models},
        **{
            alias: canonical
            for canonical, aliases in models.items()
            for alias in aliases
        },
    }
    for channel, models in FORCING_MODELS.items()
}


def channels() -> list[str]:
    """Return the recognised forcing channels."""
    return list(FORCING_MODELS)


def valid_models(channel: str) -> list[str]:
    """Return the sorted canonical model names for ``channel``."""
    try:
        return sorted(FORCING_MODELS[channel])
    except KeyError:
        raise ValueError(
            f"Unknown forcing channel {channel!r}; "
            f"choose one of {channels()}"
        ) from None


def is_valid(channel: str, model: str) -> bool:
    """True if ``model`` is a canonical name or accepted alias for ``channel``."""
    return model in _ALIAS_TO_CANONICAL.get(channel, {})


def canonical_model(channel: str, model: str) -> str:
    """Resolve a model string (canonical or alias) to its canonical name.

    Parameters
    ----------
    channel
        One of :func:`channels` (e.g. ``"hydrological"``).
    model
        The user-supplied model string.

    Returns
    -------
    str
        The canonical model name.

    Raises
    ------
    ValueError
        If ``channel`` is unknown, or ``model`` is not a recognised model or
        alias for that channel. The message lists the valid canonical names.
    """
    if channel not in FORCING_MODELS:
        raise ValueError(
            f"Unknown forcing channel {channel!r}; choose one of {channels()}"
        )
    mapping = _ALIAS_TO_CANONICAL[channel]
    if model not in mapping:
        raise ValueError(
            f"Unknown {channel} model {model!r}; "
            f"choose one of {valid_models(channel)} "
            f"(accepted aliases: {sorted(set(mapping) - set(FORCING_MODELS[channel]))})"
        )
    return mapping[model]
