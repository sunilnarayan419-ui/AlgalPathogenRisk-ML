"""Descriptive network analysis and expression overlay on provenance-tagged graphs.

Centrality, module membership and enrichment are DESCRIPTIVE. They do not show that a gene
is a pathogen determinant or that an edge is causal; edges carry their own evidence type.
"""
from __future__ import annotations

import networkx as nx
import numpy as np
import pandas as pd

from app.networks.graph import add_edge


def graph_from_edge_records(records: list[dict], source_db: str, source_version: str,
                            evidence_type: str = "predicted", interaction_type: str = "association"
                            ) -> nx.MultiGraph:
    """records: [{"a":..., "b":..., "confidence": 0-1 (optional), "evidence_type": (optional)}].
    Duplicate pairs raise (via add_edge); nothing is merged silently."""
    g = nx.MultiGraph()
    for i, r in enumerate(records):
        try:
            add_edge(g, str(r["a"]).strip(), str(r["b"]).strip(), source_db=source_db,
                     source_version=source_version, interaction_type=interaction_type,
                     evidence_type=r.get("evidence_type", evidence_type),
                     confidence=r.get("confidence"))
        except (KeyError, ValueError) as exc:
            raise ValueError(f"edge record {i}: {exc}") from exc
    return g


def _simple(g: nx.MultiGraph, min_confidence: float | None = None) -> nx.Graph:
    s = nx.Graph()
    s.add_nodes_from(g.nodes)
    for u, v, d in g.edges(data=True):
        c = d.get("confidence", -1.0)
        if min_confidence is not None and 0 <= c < min_confidence:
            continue
        s.add_edge(u, v)
    return s


def summarize(g: nx.MultiGraph, top_k: int = 10, betweenness_max_nodes: int = 3000,
              seed: int = 0) -> dict:
    """Degree/component summary; betweenness only when affordable (sampled above the limit)."""
    if g.number_of_nodes() == 0:
        return {"n_nodes": 0, "n_edges": 0, "note": "empty network"}
    s = _simple(g)
    deg = dict(s.degree())
    comps = sorted((len(c) for c in nx.connected_components(s)), reverse=True)
    out = {"n_nodes": s.number_of_nodes(), "n_edges": g.number_of_edges(),
           "n_distinct_pairs": s.number_of_edges(), "density": nx.density(s),
           "n_components": len(comps), "largest_component": comps[0],
           "component_sizes_top": comps[:10],
           "top_degree": sorted(deg.items(), key=lambda kv: (-kv[1], kv[0]))[:top_k],
           "edges_by_evidence_type": pd.Series(
               [d["evidence_type"] for *_, d in g.edges(data=True)]).value_counts().to_dict(),
           "edges_by_source": pd.Series(
               [f"{d['source_db']}@{d['source_version']}" for *_, d in g.edges(data=True)]
           ).value_counts().to_dict()}
    k = None if s.number_of_nodes() <= betweenness_max_nodes else betweenness_max_nodes // 10
    bc = nx.betweenness_centrality(s, k=k, seed=seed)
    out["top_betweenness"] = sorted(bc.items(), key=lambda kv: (-kv[1], kv[0]))[:top_k]
    out["betweenness_sampled"] = k is not None
    out["note"] = "Descriptive only; centrality does not imply biological causation."
    return out


def neighborhood(g: nx.MultiGraph, node: str, radius: int = 1) -> nx.MultiGraph:
    if node not in g:
        raise KeyError(f"node {node!r} not in network")
    if radius < 1:
        raise ValueError("radius must be >= 1")
    nodes = nx.single_source_shortest_path_length(_simple(g), node, cutoff=radius).keys()
    return g.subgraph(nodes).copy()


def filter_by_confidence(g: nx.MultiGraph, min_confidence: float) -> nx.MultiGraph:
    """Drop edges with reported confidence below the cut-off; unreported (-1) edges are kept
    and counted by the caller if that matters."""
    h = nx.MultiGraph()
    h.add_nodes_from(g.nodes(data=True))
    for u, v, k, d in g.edges(keys=True, data=True):
        if d.get("confidence", -1.0) < 0 or d["confidence"] >= min_confidence:
            h.add_edge(u, v, key=k, **d)
    return h


def overlay_de(g: nx.MultiGraph, de: pd.DataFrame, padj_col: str = "padj_bh",
               effect_col: str = "log2_diff_a_minus_b", alpha: float = 0.05,
               min_module_size: int = 2, n_perm: int = 1000, seed: int = 0) -> dict:
    """Candidate modules = connected components of the subgraph induced by significant genes.

    ``edge_enrichment`` compares the number of edges among significant genes with random gene
    sets of equal size drawn from network genes that were tested (permutation, seeded).
    """
    tested = [n for n in g.nodes if n in de.index]
    sig = [n for n in tested if pd.notna(de.at[n, padj_col]) and de.at[n, padj_col] < alpha]
    s = _simple(g)
    mods = []
    for comp in nx.connected_components(s.subgraph(sig)):
        if len(comp) >= min_module_size:
            sub = s.subgraph(comp)
            mods.append({"genes": sorted(comp), "n_edges": sub.number_of_edges(),
                         "mean_abs_effect": float(de.loc[list(comp), effect_col].abs().mean())})
    mods.sort(key=lambda m: (-len(m["genes"]), m["genes"][0]))
    rng = np.random.default_rng(seed)
    observed = s.subgraph(sig).number_of_edges() if sig else 0
    perm_p = None
    if len(sig) >= 2 and len(tested) > len(sig):
        null = np.array([s.subgraph(rng.choice(tested, len(sig), replace=False)).number_of_edges()
                         for _ in range(n_perm)])
        perm_p = float((1 + (null >= observed).sum()) / (n_perm + 1))
    return {"n_network_genes": g.number_of_nodes(), "n_tested_in_network": len(tested),
            "n_significant_in_network": len(sig), "modules": mods,
            "edge_enrichment": {"observed_edges_among_significant": observed,
                                "permutation_p": perm_p, "n_perm": n_perm, "seed": seed},
            "caveat": ("Network overlap with DE hits is hypothesis-generating. Identifier "
                       "mismatch between network and expression matrix silently shrinks "
                       "n_tested_in_network: check it.")}
