"""Exploratory run: QC, log2, correlations, PCA, optional per-gene two-group comparison.

    python scripts/run_analysis.py --fpkm data/raw/GSE128981_FPKMs.replicates.v2.tsv.gz \
        --metadata data/metadata/sample_metadata_gsm.csv --out reports/exploratory \
        [--contrast UVM4 Elow47 --batch-col batch]
Metadata CSV needs sample_id and group (batch optional). Exit codes: 0 ok, 1 invalid input,
3 contrast refused (batch-confounded).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.analysis.de_fpkm import differential_expression_log2  # noqa: E402
from app.analysis.pipeline import run_exploratory  # noqa: E402
from app.data.loader import FpkmValidationError, load_fpkm  # noqa: E402
from app.experiments.count_de import ConfoundingError, DesignError  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--fpkm", type=Path, required=True)
    ap.add_argument("--metadata", type=Path)
    ap.add_argument("--out", type=Path, default=Path("reports/exploratory"))
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--expected-samples", type=int)
    ap.add_argument("--drop-columns", nargs="*", default=None, help="annotation columns to drop")
    ap.add_argument("--contrast", nargs=2, metavar=("GROUP_A", "GROUP_B"))
    ap.add_argument("--batch-col", default=None)
    ap.add_argument("--allow-unadjusted", action="store_true")
    a = ap.parse_args()
    try:
        summary = run_exploratory(a.fpkm, a.out, metadata_csv=a.metadata, seed=a.seed,
                                  expected_samples=a.expected_samples,
                                  drop_columns=a.drop_columns)
        if a.contrast:
            if not a.metadata:
                ap.error("--contrast needs --metadata")
            fpkm, _ = load_fpkm(a.fpkm, expected_samples=a.expected_samples,
                                drop_columns=a.drop_columns)
            meta = pd.read_csv(a.metadata).set_index("sample_id")
            res, rep = differential_expression_log2(
                fpkm, meta, "group", a.contrast[0], a.contrast[1], batch_col=a.batch_col,
                allow_unadjusted=a.allow_unadjusted)
            tag = f"{a.contrast[0]}_vs_{a.contrast[1]}"
            res.to_csv(a.out / f"de_log2fpkm_{tag}.csv")
            (a.out / f"de_log2fpkm_{tag}.json").write_text(json.dumps(rep, indent=2))
            print(json.dumps(rep, indent=2))
    except (FpkmValidationError, ValueError, FileNotFoundError, DesignError) as exc:
        if isinstance(exc, ConfoundingError):
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 3
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"wrote exploratory outputs to {a.out} (pca variance {summary['pca_explained_variance_ratio'][:2]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
