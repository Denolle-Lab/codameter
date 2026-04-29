#!/usr/bin/env python
"""Top-level entry point for the dvv-workflow CLI.

This is a thin alias for the package's `dvv_workflow.cli.main`. It exists so
that you can run the workflow without installing the package via pip — for
example during development:

    python scripts/run_workflow.py run --config examples/configs/parkfield.yaml \\
        --dvv my_dvv.parquet --output runs/parkfield/

After `pip install dvv-workflow` you should prefer the installed CLI:

    dvv-workflow run --config ...
"""
from __future__ import annotations

import sys

from dvv_workflow.cli import main


if __name__ == "__main__":
    sys.exit(main())
