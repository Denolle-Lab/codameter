# Installation

`dvv-workflow` runs on Python 3.10+, on Linux and macOS. Windows is not
officially tested but should work for the pure-Python core.

## From PyPI (recommended)

```bash
# Core install — numpy / scipy / pandas / pyarrow / matplotlib
pip install dvv-workflow
```

Optional extras:

```bash
pip install "dvv-workflow[kernels]"   # adds disba for Phase 1 sensitivity kernels
pip install "dvv-workflow[mcmc]"      # adds emcee + corner for Phase 4 (v0.2+)
pip install "dvv-workflow[docs]"      # adds mkdocs + mkdocstrings
pip install "dvv-workflow[test]"      # adds pytest + pytest-cov
pip install "dvv-workflow[dev]"       # everything above + black/ruff/mypy/pre-commit
```

## From source

```bash
git clone https://github.com/Denolle-Lab/dvv-workflow.git
cd dvv-workflow
pip install -e ".[dev]"
pre-commit install
pytest
```

## With conda

```bash
conda env create -f environment.yml
conda activate dvv-workflow
```

## Verifying the install

```bash
python -c "import dvv_workflow; print(dvv_workflow.__version__)"
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
