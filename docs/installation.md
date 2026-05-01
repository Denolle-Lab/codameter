# Installation

`codameter` runs on Python 3.10+, on Linux and macOS. Windows is not
officially tested but should work for the pure-Python core.

## From PyPI (recommended)

```bash
# Core install — numpy / scipy / pandas / pyarrow / matplotlib
pip install codameter
```

Optional extras:

```bash
pip install "codameter[kernels]"   # adds disba for Phase 1 sensitivity kernels
pip install "codameter[mcmc]"      # adds emcee + corner for Phase 4 (v0.2+)
pip install "codameter[docs]"      # adds mkdocs + mkdocstrings
pip install "codameter[test]"      # adds pytest + pytest-cov
pip install "codameter[dev]"       # everything above + black/ruff/mypy/pre-commit
```

## From source

```bash
git clone https://github.com/Denolle-Lab/codameter.git
cd codameter
pip install -e ".[dev]"
pre-commit install
pytest
```

## With conda

```bash
conda env create -f environment.yml
conda activate codameter
```

## Optional: California CVM / SCEC UCVM access

`codameter` can build California site velocity models from SCEC UCVM when a
local `ucvm_query` command is available. UCVM is an external SCEC package with
large model files, so it is not bundled into the Python wheel. Use one of the
options below for California deployments.

### Option A — native UCVM install

Install UCVM from SCEC, including the California models you need, then point
`codameter` at the resulting executable and config file:

```yaml
velocity_model:
   source: auto
property_sources:
   enabled: true
   order: [ucvm, usgs_vs30, default]
   ucvm:
      executable: /path/to/ucvm_query
      config_path: /path/to/ucvm/conf/ucvm.conf
      models: [cvmsi, cvms5, cvms, cvmh]
```

### Option B — Docker-backed `ucvm_query` wrapper

If Docker is available, install a lightweight wrapper from this repository:

```bash
pixi run install-ucvm-query
# or, without pixi:
python scripts/install_ucvm_query_docker.py
```

The wrapper defaults to SCEC's `sceccode/ucvm_257_cvmsi:0801` image and writes
`.codameter/bin/ucvm_query`. Use it directly in YAML:

```yaml
velocity_model:
   source: auto
property_sources:
   enabled: true
   order: [ucvm, usgs_vs30, default]
   ucvm:
      executable: .codameter/bin/ucvm_query
      models: [cvmsi]
```

Alternatively, skip the wrapper and let `codameter` call Docker directly:

```yaml
property_sources:
   ucvm:
      docker_image: sceccode/ucvm_257_cvmsi:0801
      models: [cvmsi]
```

For broader California coverage, install/use images or native models matching
your region. Common UCVM model keys include `cvmsi`, `cvms5`, `cvms`, `cvmh`,
`cca`, `cs173`, `cs173h`, and `cencal`; some are many GB to tens of GB.

## Verifying the install

```bash
python -c "import codameter; print(codameter.__version__)"
# 0.1.0

python examples/01_parkfield_synthetic.py --no-plot
# ... should print "[OK] all parameters recovered within 4σ."

python examples/02_clements_denolle_2023.py --no-plot
# ... should print "[OK] chi^2_red = ...; pipeline completed successfully."
```

## Optional: the Clements & Denolle (2023) data

For real-data testing of the C&D harness:

1. Download the Zenodo archive (4.4 GB):
   <https://doi.org/10.5281/zenodo.6413275>
2. Unpack into a directory of your choice:
   ```bash
   unzip clements_denolle_2023_data-0.2.0.zip -d /scratch/cd2023/
   ```
3. Run the harness against it:
   ```bash
   python examples/02_clements_denolle_2023.py \
       --data-dir /scratch/cd2023/ --station CI.LJR \
       --output runs/cd2023_CI_LJR/
   ```

The synthetic mode (default) lets you validate the wiring before
committing to the download.
