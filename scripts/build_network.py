"""Build a provenance-tagged network from STRING and/or BioGRID files and write GraphML + report.

    python scripts/build_network.py --string links.txt.gz --string-version v12.0 \
        --expression data/raw/GSE128981_FPKMs.replicates.v2.tsv.gz --out reports/network
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.networks import analysis, loaders  # noqa: E402
from app.networks.graph import write_graphml  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--string", type=Path)
    ap.add_argument("--string-version")
    ap.add_argument("--min-score", type=int, default=700)
    ap.add_argument("--biogrid", type=Path)
    ap.add_argument("--biogrid-version")
    ap.add_argument("--expression", type=Path, help="TSV(.gz) with gene ids in column 1")
    ap.add_argument("--out", type=Path, default=Path("reports/network"))
    a = ap.parse_args()
    if not (a.string or a.biogrid):
        ap.error("provide --string and/or --biogrid")
    if (a.string and not a.string_version) or (a.biogrid and not a.biogrid_version):
        ap.error("each source needs its --*-version (provenance is mandatory)")
    try:
        graphs, reports = [], {}
        if a.string:
            g, r = loaders.load_string_links(a.string, source_version=a.string_version,
                                             min_combined_score=a.min_score)
            graphs.append(g)
            reports["string"] = r
        if a.biogrid:
            g, r = loaders.load_biogrid_tab3(a.biogrid, source_version=a.biogrid_version)
            graphs.append(g)
            reports["biogrid"] = r
        g = loaders.merge_graphs(*graphs)
        out = {"load_reports": reports, "summary": analysis.summarize(g)}
        if a.expression:
            ids = pd.read_csv(a.expression, sep="\t", usecols=[0], compression="infer").iloc[:, 0]
            out["expression_overlap"] = loaders.expression_overlap(g, ids)
            frac = out["expression_overlap"]["fraction_nodes_in_expression"]
            if frac is not None and frac < 0.5:
                out["warning"] = ("fewer than half of network nodes match expression ids: likely "
                                  "an identifier/genome-version mismatch; do not interpret.")
    except (loaders.NetworkLoadError, ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    a.out.mkdir(parents=True, exist_ok=True)
    write_graphml(g, a.out / "network.graphml")
    (a.out / "network_report.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out["summary"], indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
