"""Audit a GEO series matrix and/or an expression table. Writes JSON + Markdown.

    python scripts/audit_dataset.py --series-matrix data/raw/GSE128981_series_matrix.txt.gz \
        [--expression data/raw/GSE128981_FPKMs.replicates.v2.tsv.gz] --out reports/audit
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.data import geo  # noqa: E402
from app.data.loader import sha256_file  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--series-matrix", type=Path, required=True)
    ap.add_argument("--expression", type=Path, help="genes x samples TSV(.gz), first column = id")
    ap.add_argument("--out", type=Path, default=Path("reports/audit"))
    ap.add_argument("--group-col", default="char_genotype")
    a = ap.parse_args()
    try:
        s = geo.parse_geo_series_matrix(a.series_matrix)
    except (geo.GeoParseError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    expr, expr_prov = s.expression, None
    if a.expression:
        expr = pd.read_csv(a.expression, sep="\t", index_col=0, compression="infer")
        expr_prov = {"path": str(a.expression), "sha256": sha256_file(a.expression),
                     "size_bytes": a.expression.stat().st_size}
    report = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "accession": s.accession, "series_title": (s.series.get("Series_title") or [""])[0],
        "provenance": {"series_matrix": s.provenance, "expression": expr_prov},
        "n_samples": len(s.samples),
        "organism": sorted(set(s.samples.get("organism_ch1", []))),
        "assay": sorted(set(s.samples.get("library_strategy", []))),
        "group_sizes": {c: s.samples[c].value_counts().to_dict()
                        for c in s.samples if c.startswith("char_")},
        "alignment": geo.check_metadata_alignment(s.samples, expr),
        "qc": geo.expression_qc(expr) if expr is not None else None,
        "suitability": geo.suitability(s.samples, expr, a.group_col),
    }
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    sut = report["suitability"]
    md = [f"# Audit: {s.accession}", "", f"- Series: {report['series_title']}",
          f"- Samples: {report['n_samples']}; organism: {', '.join(report['organism'])}; "
          f"assay: {', '.join(report['assay'])}",
          f"- Expression values present: {expr is not None}", "",
          "**Supports:** " + ("; ".join(sut["supports"]) or "nothing yet"), "",
          "**Does not support:** " + "; ".join(sut["does_not_support"])]
    (a.out / "audit.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"samples": report["n_samples"], "expression_present": expr is not None,
                      "supports": sut["supports"], "does_not_support": sut["does_not_support"]},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
