"""Train + evaluate the tabular classifier from a CSV and save an artifact.

    python scripts/train_model.py --demo --out models/current          # SYNTHETIC data
    python scripts/train_model.py --csv labelled.csv --target label \
        --group-column group --out models/current

Never point this at GSE128981 genotype columns and call the result "risk": that dataset
has no infection or collapse outcome labels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.ml import pipeline as mlp  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--csv", type=Path)
    ap.add_argument("--demo", action="store_true", help="use SYNTHETIC demonstration data")
    ap.add_argument("--target", default="label")
    ap.add_argument("--group-column", default="group")
    ap.add_argument("--no-groups", action="store_true", help="samples are independent")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=Path("models/current"))
    ap.add_argument("--report", type=Path, default=None, help="also write the report JSON here")
    a = ap.parse_args()
    if a.demo == bool(a.csv):
        ap.error("provide exactly one of --demo or --csv")
    if a.demo:
        df, prov = mlp.make_demo_dataset(seed=a.seed), {"source": "synthetic"}
    else:
        df = pd.read_csv(a.csv)
        prov = {"source": str(a.csv), "sha256": hashlib.sha256(a.csv.read_bytes()).hexdigest()}
    cfg = mlp.TrainConfig(target=a.target, group_column=None if a.no_groups else a.group_column,
                          seed=a.seed, synthetic=a.demo)
    report = mlp.train_and_evaluate(df, cfg, out_dir=a.out, dataset_provenance=prov)
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("selected_model", "threshold", "test_metrics",
                                              "caveats", "artifact_dir")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
