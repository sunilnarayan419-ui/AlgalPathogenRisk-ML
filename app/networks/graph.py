"""Evidence-traceable interaction graph. Every edge needs a source and provenance."""
from __future__ import annotations

import networkx as nx

EVIDENCE_TYPES = {"experimental", "curated", "predicted", "text_mining"}


def add_edge(g: nx.MultiGraph, a: str, b: str, *, source_db: str, source_version: str,
             interaction_type: str, evidence_type: str, confidence: float | None = None,
             evidence_ids: list[str] | None = None,
             attributes: dict[str, str | int | float | bool] | None = None) -> None:
    if not a or not b:
        raise ValueError("Node identifiers must be non-empty.")
    if a == b:
        raise ValueError("Self-interactions are not accepted by this builder.")
    if not source_db or not source_version:
        raise ValueError("Edge provenance requires source_db and source_version.")
    if evidence_type not in EVIDENCE_TYPES:
        raise ValueError(f"evidence_type must be one of {sorted(EVIDENCE_TYPES)}.")
    if confidence is not None and not 0 <= confidence <= 1:
        raise ValueError("confidence must be in [0, 1].")
    reserved = {"source_db", "source_version", "interaction_type", "evidence_type",
                "confidence", "evidence_ids"}
    extra = dict(attributes or {})
    if reserved & extra.keys():
        raise ValueError(f"attributes may not override {sorted(reserved & extra.keys())}.")
    if any(not isinstance(v, str | int | float | bool) for v in extra.values()):
        raise ValueError("attributes must be scalar (str/int/float/bool) to survive GraphML.")
    key = f"{source_db}|{interaction_type}"
    if g.has_edge(a, b, key):
        raise ValueError(f"Duplicate edge {a}-{b} for {key}; merge evidence explicitly.")
    g.add_edge(a, b, key=key, source_db=source_db, source_version=source_version,
               interaction_type=interaction_type, evidence_type=evidence_type,
               confidence=-1.0 if confidence is None else float(confidence),  # -1 = not reported
               evidence_ids=";".join(evidence_ids or []), **extra)


def metrics(g: nx.MultiGraph) -> dict:
    if g.number_of_nodes() == 0:
        return {"n_nodes": 0, "n_edges": 0, "note": "empty network"}
    simple = nx.Graph(g)
    degs = [d for _, d in simple.degree()]
    return {"n_nodes": g.number_of_nodes(), "n_edges": g.number_of_edges(),
            "density": nx.density(simple), "n_components": nx.number_connected_components(simple),
            "max_degree": max(degs),
            "n_experimental_edges": sum(1 for *_, d in g.edges(data=True)
                                        if d["evidence_type"] == "experimental"),
            "note": "Descriptive only; centrality does not imply biological causation."}


def write_graphml(g: nx.MultiGraph, path) -> None:
    nx.write_graphml(g, path)


def read_graphml(path) -> nx.MultiGraph:
    g = nx.read_graphml(path)
    return nx.MultiGraph(g) if not g.is_multigraph() else g
