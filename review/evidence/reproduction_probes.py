"""Read-only artifact inventory; writes an aggregation probe under review/."""
import hashlib
import importlib.metadata as im
import json
import re
from argparse import Namespace
from pathlib import Path

import codameter
import pandas as pd
import pyarrow.ipc as ipc
from codameter import bench, synthetic_demo

out = Path("review/evidence")
figs = re.findall(
    r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}",
    Path("paper/manuscript_marine.qmd").read_text(),
)
report = {
    "source_version": codameter.__version__,
    "installed_metadata_version": im.version("codameter"),
    "figures_not_regenerated_by_build_figures": [
        f for f in figs if Path(f).stem not in synthetic_demo.FIGURES
    ],
    "realdata": {},
}
for sta in ["LJR", "ARV", "RXH"]:
    p = Path(f"paper/data/gate1/dvv2y/band=2.0-4.0/CI.{sta}.parquet")
    d = pd.read_parquet(p)
    date = pd.to_datetime(d["date"])
    a = Path(f"paper/data/gate1/legacy_cd2022/CI.{sta}.arrow")
    legacy = ipc.open_file(a).read_all().to_pandas()
    report["realdata"][sta] = {
        "rows": len(d),
        "date_min": str(date.min()),
        "date_max": str(date.max()),
        "unique_dates": int(date.nunique()),
        "duplicates": int(date.duplicated().sum()),
        "rows_after_150_calendar_days": int(
            (date >= date.min() + pd.Timedelta(days=150)).sum()
        ),
        "columns": list(d.columns),
        "legacy_rows": len(legacy),
        "legacy_columns": list(legacy.columns),
        "parquet_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
    }
probe = out / "aggregation_probe"
probe.mkdir(exist_ok=True)
row = {"case_id": "probe", "config_index": 0, "ok": False, "rms": None}
(probe / "shard-00000-of-00002.jsonl").write_text(
    json.dumps(row) + "\n" + json.dumps(row) + "\n"
)
exitcode = bench._cmd_aggregate(Namespace(src=str(probe), out=str(probe / "aggregate")))
report["aggregate_incomplete_duplicate_probe"] = {
    "declared_shards": 2,
    "present_shards": 1,
    "duplicate_rows": 2,
    "exit_code": exitcode,
}
(out / "reproduction_probes.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
