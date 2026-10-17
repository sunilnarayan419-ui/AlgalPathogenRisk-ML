"""Count-based DE (PyDESeq2) with batch-estimability guards. Needs RAW counts (not FPKM).

    python scripts/run_count_de.py --counts counts.tsv --metadata data/metadata/sample_manifest.csv \
        --group-col strain --batch-col batch --list-estimable
    python scripts/run_count_de.py ... --group-a UVM11 --group-b Elow47
Exit codes: 0 ok, 1 invalid input, 2 usage, 3 refused by a design guard.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.data.counts import CountsValidationError, align_metadata, load_counts  # noqa: E402
from app.experiments import count_de as cd  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--counts", type=Path, required=True)
    ap.add_argument("--metadata", type=Path, required=True)
    ap.add_argument("--sample-col", default="sample_accession")
    ap.add_argument("--group-col", default="strain")
    ap.add_argument("--batch-col", default=None)
    ap.add_argument("--group-a"); ap.add_argument("--group-b")  # noqa: E702
    ap.add_argument("--list-estimable", action="store_true")
    ap.add_argument("--use-all-samples", action="store_true")
    ap.add_argument("--allow-unadjusted", action="store_true")
    ap.add_argument("--round-noninteger", action="store_true")
    ap.add_argument("--sample-map", type=Path, help="CSV column_name,sample_id")
    ap.add_argument("--out", type=Path, default=Path("reports/count_de"))
    a = ap.parse_args()
    if not a.list_estimable and not (a.group_a and a.group_b):
        print("provide --list-estimable or both --group-a and --group-b", file=sys.stderr)
        return 2
    try:
        smap = None
        if a.sample_map:
            m = pd.read_csv(a.sample_map)
            smap = dict(zip(m["column_name"], m["sample_id"], strict=True))
        counts, _ = load_counts(a.counts, sample_map=smap, round_noninteger=a.round_noninteger)
        meta = align_metadata(counts, pd.read_csv(a.metadata), sample_col=a.sample_col,
                              required=(a.group_col,) + ((a.batch_col,) if a.batch_col else ()))
        a.out.mkdir(parents=True, exist_ok=True)
        if a.list_estimable:
            t = cd.estimable_contrasts(meta, a.group_col, a.batch_col)
            t.to_csv(a.out / "estimable_contrasts.csv", index=False)
            print(t.to_string(index=False))
            return 0
        res, rep = cd.run_deseq2(counts, meta, a.group_col, a.group_a, a.group_b,
                                 batch_col=a.batch_col, use_all_samples=a.use_all_samples,
                                 allow_unadjusted=a.allow_unadjusted)
        tag = f"{a.group_a}_vs_{a.group_b}"
        res.to_csv(a.out / f"de_{tag}.csv")
        (a.out / f"de_{tag}.json").write_text(json.dumps(rep, indent=2))
        print(json.dumps(rep, indent=2))
        return 0
    except cd.ConfoundingError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 3
    except (CountsValidationError, cd.DesignError, ValueError, FileNotFoundError, ImportError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
