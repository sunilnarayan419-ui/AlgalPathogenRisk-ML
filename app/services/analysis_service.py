"""Pure-Python service layer behind the analysis/network API routes (unit-testable)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.analysis.de_fpkm import differential_expression_log2
from app.networks import analysis as na

MAX_GENES, MAX_SAMPLES = 5000, 200


class PayloadError(ValueError):
    """Request payload is structurally invalid (HTTP 422)."""


def de_from_payload(p: dict) -> dict:
    gene_ids, sample_ids, values = p["gene_ids"], p["sample_ids"], p["values"]
    if not gene_ids or not sample_ids:
        raise PayloadError("gene_ids and sample_ids must be non-empty.")
    if len(gene_ids) > MAX_GENES or len(sample_ids) > MAX_SAMPLES:
        raise PayloadError(f"at most {MAX_GENES} genes and {MAX_SAMPLES} samples per request.")
    if len(values) != len(gene_ids) or any(len(r) != len(sample_ids) for r in values):
        raise PayloadError("values must be genes x samples and match gene_ids/sample_ids.")
    if len(set(gene_ids)) != len(gene_ids) or len(set(sample_ids)) != len(sample_ids):
        raise PayloadError("duplicate gene or sample identifiers.")
    groups = p["groups"]
    if set(groups) != set(sample_ids):
        raise PayloadError("groups must have exactly one entry per sample id.")
    meta = pd.DataFrame({"group": pd.Series(groups)})
    batches = p.get("batches")
    if batches:
        if set(batches) != set(sample_ids):
            raise PayloadError("batches must have exactly one entry per sample id.")
        meta["batch"] = pd.Series(batches)
    fpkm = pd.DataFrame(np.asarray(values, dtype=float), index=gene_ids, columns=sample_ids)
    res, report = differential_expression_log2(
        fpkm, meta, "group", p["group_a"], p["group_b"],
        batch_col="batch" if batches else None,
        allow_unadjusted=bool(p.get("allow_unadjusted", False)))
    top = res.head(int(p.get("top_n", 50))).reset_index()
    return {"report": report, "results": top.replace({np.nan: None}).to_dict("records")}


def network_from_payload(p: dict) -> dict:
    recs = p["edges"]
    if not recs or len(recs) > 50000:
        raise PayloadError("edges must contain between 1 and 50000 records.")
    g = na.graph_from_edge_records(recs, p["source_db"], p["source_version"],
                                   evidence_type=p.get("evidence_type", "predicted"))
    out = {"summary": na.summarize(g, top_k=int(p.get("top_k", 10)))}
    if p.get("node"):
        try:
            nb = na.neighborhood(g, p["node"], int(p.get("radius", 1)))
        except KeyError as exc:
            raise PayloadError(str(exc)) from exc
        out["neighborhood"] = {"nodes": sorted(nb.nodes), "n_edges": nb.number_of_edges()}
    return out
