"""Audit GEO series-matrix metadata and optionally write sample manifests.

    python scripts/audit_geo_matrix.py --input data/raw/GSE128981_series_matrix.txt.gz \
        --output reports/geo_metadata_audit.json --manifest-dir data/metadata --gse128981-batch-rule
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.metadata import audit_geo_series_matrix, build_sample_manifest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    parser.add_argument("--manifest-dir", help="write sample_manifest.csv and sample_metadata_*.csv")
    parser.add_argument("--gse128981-batch-rule", action="store_true",
                        help="infer batch from accession blocks (GSE128981 only; see data dictionary)")
    args = parser.parse_args()
    result = audit_geo_series_matrix(args.input)
    if not result["exists"]:
        print(f"ERROR: {result['error']}: {args.input}", file=sys.stderr)
        return 1
    if args.manifest_dir:
        manifest = build_sample_manifest(result, args.gse128981_batch_rule)
        out = Path(args.manifest_dir)
        out.mkdir(parents=True, exist_ok=True)
        manifest.to_csv(out / "sample_manifest.csv", index=False)
        for key, name in (("sample_accession", "sample_metadata_gsm.csv"),
                          ("title", "sample_metadata_title.csv")):
            df = manifest[[key, "strain", "genotype", "batch"]].rename(
                columns={key: "sample_id", "strain": "group"})
            df.to_csv(out / name, index=False)
    payload = json.dumps(result, indent=2)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload + "\n", encoding="utf-8")
    print(payload if not args.manifest_dir else json.dumps(
        {k: result[k] for k in ("accession", "sample_count_from_accessions",
                                "expression_matrix_has_gene_rows")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
