from __future__ import annotations

import os
from pathlib import Path

import pytest

from codameter.config import Location, Measurement, Site
from codameter.data.property_providers import (
    DefaultPropertyProvider,
    UCVMProvider,
    USGSVs30Provider,
    default_velocity_model,
    resolve_site_properties,
)


def test_default_provider_returns_valid_layers():
    loc = Location(lat=34.55, lon=-117.77)
    meas = Measurement(frequency_band_hz=(2.0, 4.0))
    result = DefaultPropertyProvider(profile="california_alluvium").resolve(
        loc, meas, max_depth_m=1000.0
    )

    assert result.velocity_model is not None
    assert result.velocity_model.source == "default:california_alluvium"
    assert result.material_properties is not None
    assert result.confidence == "low"
    assert result.warnings
    assert result.velocity_model.layers[0].thickness_km == pytest.approx(0.03)


def test_usgs_vs30_provider_builds_shallow_layer():
    loc = Location(lat=34.55, lon=-117.77)
    meas = Measurement(frequency_band_hz=(2.0, 4.0))
    result = USGSVs30Provider(vs30_m_s=450.0).resolve(
        loc, meas, max_depth_m=1000.0
    )

    assert not isinstance(result, type(None))
    assert result.velocity_model is not None
    top = result.velocity_model.layers[0]
    assert top.thickness_km == pytest.approx(0.03)
    assert top.vs == pytest.approx(0.45)
    assert top.vp > top.vs * 2**0.5
    assert result.confidence == "medium"


def test_provider_chain_falls_back_to_usgs_when_ucvm_missing():
    loc = Location(lat=34.55, lon=-117.77)
    meas = Measurement(frequency_band_hz=(2.0, 4.0))
    result = resolve_site_properties(
        loc,
        meas,
        property_sources={
            "order": ["ucvm", "usgs_vs30", "default"],
            "ucvm": {"executable": "/definitely/not/ucvm_query"},
            "usgs": {"vs30_m_s": 360.0},
        },
    )

    assert result.velocity_model is not None
    assert result.source == "usgs:vs30"
    assert any("ucvm" in warning for warning in result.warnings)


def test_provider_chain_falls_back_to_defaults_when_all_external_miss():
    loc = Location(lat=34.55, lon=-117.77)
    meas = Measurement(frequency_band_hz=(2.0, 4.0))
    result = resolve_site_properties(
        loc,
        meas,
        property_sources={
            "order": ["ucvm", "usgs_vs30", "default"],
            "ucvm": {"executable": "/definitely/not/ucvm_query"},
        },
    )

    assert result.velocity_model is not None
    assert result.source == "default:california_alluvium"
    assert result.confidence == "low"
    assert len(result.warnings) >= 2


def test_ucvm_provider_parses_local_command(tmp_path: Path):
    exe = tmp_path / "ucvm_query"
    # Mock reads lon/lat/depth lines from stdin and prints one UCVM columnar
    # result line per depth (last 3 numeric cols = cmb_vp, cmb_vs, cmb_rho).
    exe.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "assert '-m' in sys.argv\n"
        "assert '-l' not in sys.argv, 'should use stdin, not -l'\n"
        "for raw in sys.stdin:\n"
        "    line = raw.strip()\n"
        "    if not line:\n"
        "        continue\n"
        "    lon, lat, depth = line.split()[:3]\n"
        "    print(f'  {lon}  {lat}  {depth}  280.0  400.0  mock"
        "  1800.0  700.0  2000.0  none  0.0  0.0  0.0  crust  1800.0  700.0  2000.0')\n"
    )
    exe.chmod(exe.stat().st_mode | 0o111)

    loc = Location(lat=34.55, lon=-117.77)
    meas = Measurement(frequency_band_hz=(2.0, 4.0))
    result = UCVMProvider(
        executable=str(exe),
        model="mock",
        depth_m=(0.0, 30.0, 100.0),
    ).resolve(loc, meas, max_depth_m=100.0)

    assert result.velocity_model is not None
    assert result.velocity_model.source == "ucvm:mock"
    first = result.velocity_model.layers[0]
    assert first.thickness_km == pytest.approx(0.03)
    assert first.vp == pytest.approx(1.8)
    assert first.vs == pytest.approx(0.7)
    assert first.rho == pytest.approx(2.0)


def test_ucvm_provider_tries_multiple_models(tmp_path: Path):
    exe = tmp_path / "ucvm_query"
    exe.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "model = sys.argv[sys.argv.index('-m') + 1]\n"
        "if model == 'bad':\n"
        "    raise SystemExit(2)\n"
        "for raw in sys.stdin:\n"
        "    line = raw.strip()\n"
        "    if not line:\n"
        "        continue\n"
        "    lon, lat, depth = line.split()[:3]\n"
        "    print(f'  {lon}  {lat}  {depth}  280.0  400.0  mock"
        "  2000.0  800.0  2100.0  none  0.0  0.0  0.0  crust  2000.0  800.0  2100.0')\n"
    )
    exe.chmod(exe.stat().st_mode | 0o111)

    loc = Location(lat=34.55, lon=-117.77)
    meas = Measurement(frequency_band_hz=(2.0, 4.0))
    result = UCVMProvider(
        executable=str(exe),
        model=["bad", "good"],
        depth_m=(0.0, 30.0),
    ).resolve(loc, meas, max_depth_m=30.0)

    assert result.velocity_model is not None
    assert result.velocity_model.source == "ucvm:good"
    assert result.provenance["models_tried"] == ["bad", "good"]


def test_ucvm_provider_can_use_docker_image(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    docker = tmp_path / "docker"
    # Mock Docker binary: verify correct flags for Apple-Silicon-compatible
    # invocation (--platform linux/amd64, -e LD_LIBRARY_PATH, --entrypoint,
    # -f config) and stdin-based batch querying.
    docker.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "assert 'run' in sys.argv\n"
        "assert '--rm' in sys.argv\n"
        "assert '-i' in sys.argv\n"
        "assert '--platform' in sys.argv\n"
        "assert '--entrypoint' in sys.argv\n"
        "assert '-e' in sys.argv\n"
        "assert '-f' in sys.argv, 'missing -f config flag'\n"
        "assert '-m' in sys.argv\n"
        "assert '-l' not in sys.argv, 'should use stdin, not -l'\n"
        "for raw in sys.stdin:\n"
        "    line = raw.strip()\n"
        "    if not line:\n"
        "        continue\n"
        "    lon, lat, depth = line.split()[:3]\n"
        "    print(f'  {lon}  {lat}  {depth}  280.0  400.0  cvmsi"
        "  1900.0  750.0  2050.0  none  0.0  0.0  0.0  crust  1900.0  750.0  2050.0')\n"
    )
    docker.chmod(docker.stat().st_mode | 0o111)
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ.get('PATH', '')}")

    loc = Location(lat=34.55, lon=-117.77)
    meas = Measurement(frequency_band_hz=(2.0, 4.0))
    result = UCVMProvider(
        executable="missing_ucvm_query",
        docker_image="sceccode/ucvm_257_cvmsi:0801",
        model="cvmsi",
        depth_m=(0.0, 30.0),
    ).resolve(loc, meas, max_depth_m=30.0)

    assert result.velocity_model is not None
    assert result.velocity_model.source == "ucvm:cvmsi"
    assert result.provenance["executable"] == "docker:sceccode/ucvm_257_cvmsi:0801"
    assert result.provenance["docker_image"] == "sceccode/ucvm_257_cvmsi:0801"


def test_site_from_dict_auto_uses_provider_resolution():
    site = Site.from_dict(
        {
            "site_id": "auto_ljr",
            "location": {"lat": 34.55, "lon": -117.77, "elevation_m": 830.0},
            "measurement": {"type": "cross_correlation", "frequency_band_hz": [2.0, 4.0]},
            "velocity_model": {"source": "auto"},
            "property_sources": {
                "enabled": True,
                "order": ["usgs_vs30", "default"],
                "usgs": {"vs30_m_s": 500.0},
            },
            "material_properties": {
                "porosity_prior": {"mean": 0.2, "std": 0.05},
            },
        }
    )

    assert site.velocity_model.source == "usgs:vs30"
    assert site.velocity_model.layers[0].vs == pytest.approx(0.5)
    assert site.material_properties.porosity_prior.mean == pytest.approx(0.2)
    assert site.metadata["property_resolution"]["source"] == "usgs:vs30"


def test_default_velocity_model_profiles_are_valid():
    for profile in ["california_alluvium", "california_rock", "volcanic"]:
        vm = default_velocity_model(profile)
        assert vm.layers
        for layer in vm.layers:
            assert layer.vp > layer.vs * 2**0.5
            assert layer.rho > 0
