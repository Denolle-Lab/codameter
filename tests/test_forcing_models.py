"""Tests for the forcing-model registry and Site validation."""
from __future__ import annotations

import pytest

from codameter.config import (
    AnalysisConfig,
    Forcings,
    ForcingSpec,
    Layer,
    Location,
    Measurement,
    Site,
    VelocityModel,
)
from codameter.forcing_models import (
    canonical_model,
    is_valid,
    valid_models,
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_canonical_model_resolves_aliases():
    assert canonical_model("hydrological", "okubo2024") == "baseflow"
    assert canonical_model("hydrological", "roeloffs1988") == "drained"
    assert canonical_model("thermoelastic", "phase_shift") == "berger"
    assert canonical_model("damage", "snieder2017") == "snieder_healing"


def test_canonical_model_passes_through_canonical_names():
    assert canonical_model("hydrological", "baseflow") == "baseflow"
    assert canonical_model("loading", "snowpack") == "snowpack"


def test_canonical_model_unknown_raises_with_choices():
    with pytest.raises(ValueError) as exc:
        canonical_model("hydrological", "not_a_model")
    msg = str(exc.value)
    assert "not_a_model" in msg
    assert "baseflow" in msg  # lists valid options


def test_unknown_channel_raises():
    with pytest.raises(ValueError):
        canonical_model("nonsense", "baseflow")


def test_is_valid_and_valid_models():
    assert is_valid("hydrological", "okubo2024")
    assert not is_valid("hydrological", "bogus")
    assert "baseflow" in valid_models("hydrological")
    assert "drained" in valid_models("hydrological")


# ---------------------------------------------------------------------------
# Construction-time validation
# ---------------------------------------------------------------------------


def test_forcings_reject_unknown_model():
    with pytest.raises(ValueError) as exc:
        Forcings(hydrological=ForcingSpec(enabled=True, model="totally_wrong"))
    assert "totally_wrong" in str(exc.value)


def test_forcings_accept_alias_models():
    # Aliases used across the repo must remain valid.
    Forcings(
        thermoelastic=ForcingSpec(enabled=True, model="phase_shift"),
        hydrological=ForcingSpec(enabled=True, model="okubo2024"),
        damage=ForcingSpec(enabled=True, model="snieder2017"),
    )
    Forcings(hydrological=ForcingSpec(enabled=True, model="roeloffs1988"))


# ---------------------------------------------------------------------------
# Site.validate()
# ---------------------------------------------------------------------------


def _minimal_site(**forcing_kwargs) -> Site:
    return Site(
        site_id="t",
        location=Location(lat=0.0, lon=0.0),
        measurement=Measurement(frequency_band_hz=(0.5, 2.0)),
        velocity_model=VelocityModel(
            layers=[Layer(thickness_km=1.0, vp=2.0, vs=1.0, rho=2.0)]
        ),
        forcings=Forcings(**forcing_kwargs),
        analysis=AnalysisConfig(),
    )


def test_validate_clean_site_returns_no_issues():
    site = _minimal_site(
        hydrological=ForcingSpec(enabled=True, model="baseflow")
    )
    assert site.validate() == []


def test_validate_raises_when_no_forcing_enabled():
    site = _minimal_site()
    with pytest.raises(ValueError):
        site.validate()


def test_validate_flags_invalid_model_set_after_construction():
    site = _minimal_site(
        hydrological=ForcingSpec(enabled=True, model="baseflow")
    )
    # Bypass construction-time validation to mimic post-hoc tampering.
    object.__setattr__(site.forcings.hydrological, "model", "bogus")
    issues = site.validate()
    assert any("bogus" in m for m in issues)


def test_validate_flags_bad_date_range_and_mcmc():
    site = _minimal_site(
        hydrological=ForcingSpec(enabled=True, model="baseflow")
    )
    site.analysis = AnalysisConfig(
        start_date="2020-01-01",
        end_date="2010-01-01",
        uncertainty_method="mcmc",
    )
    issues = site.validate()
    assert any("start_date" in m for m in issues)
    assert any("mcmc" in m for m in issues)
