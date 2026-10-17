"""Loaders that turn STRING / BioGRID flat files into provenance-tagged graphs.

Design rules
------------
* Every edge goes through :func:`app.networks.graph.add_edge`, so source, version and
  evidence type are always recorded.
* Parsing is strict: malformed rows raise :class:`NetworkLoadError` with line numbers
  instead of being skipped silently.
* Identifier normalisation (isoform -> gene) is explicit and configurable. Collapsing
  isoforms can create self-pairs and duplicate pairs; both are counted in the load report
  and never hidden. Duplicate pairs keep the *maximum* channel score.
* Nothing is downloaded here and no interaction data ships with the repository.

These loaders have NOT been run against the real STRING / BioGRID files by the authors:
check ``report`` (``n_rows_read``, ``n_edges``) and the identifier overlap with your
expression matrix (:func:`expression_overlap`) before drawing any conclusion.
"""
from __future__ import annotations

import csv
import gzip
import io
import re
import zipfile
from collections.abc import Callable, Iterator
from pathlib import Path

import networkx as nx

from app.networks.graph import add_edge

CHLAMYDOMONAS_TAXON_ID = 3055

STRING_CHANNELS = ("neighborhood", "fusion", "cooccurence", "coexpression",
                   "experimental", "database", "textmining")
# channel -> evidence_type in app.networks.graph.EVIDENCE_TYPES
_CHANNEL_EVIDENCE = {"experimental": "experimental", "database": "curated",
                     "textmining": "text_mining"}
_EVIDENCE_PRIORITY = ("experimental", "database", "textmining")  # ties resolved in this order

BIOGRID_REQUIRED_COLUMNS = (
    "#BioGRID Interaction ID", "Systematic Name Interactor A", "Systematic Name Interactor B",
    "Official Symbol Interactor A", "Official Symbol Interactor B",
    "Experimental System Type", "Organism ID Interactor A", "Organism ID Interactor B",
)

IdNormalizer = Callable[[str], str]


class NetworkLoadError(ValueError):
    def __init__(self, issues: list[str]):
        super().__init__("Network load failed: " + "; ".join(issues))
        self.issues = issues


# --------------------------------------------------------------------------- identifiers
_TAXON_PREFIX = re.compile(r"^\d+\.")
_TRANSCRIPT_SUFFIX = re.compile(r"\.t\d+(\.\d+)*$")


def default_gene_id(raw: str) -> str:
    """'3055.Cre01.g000050.t1.1' -> 'Cre01.g000050'.

    Strips an NCBI taxon prefix and a Phytozome-style transcript suffix. Your expression
    matrix may use a different naming scheme/genome version: pass your own normalizer.
    """
    s = _TAXON_PREFIX.sub("", raw.strip())
    return _TRANSCRIPT_SUFFIX.sub("", s)


def identity_id(raw: str) -> str:
    return raw.strip()


# --------------------------------------------------------------------------- file helpers
def _open_text(path: Path) -> io.TextIOBase:
    """Open plain, .gz or single-member .zip text files."""
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found.")
    if path.suffix == ".gz":
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", newline="")
    if path.suffix == ".zip":
        zf = zipfile.ZipFile(path)
        names = [n for n in zf.namelist() if not n.endswith("/")]
        if len(names) != 1:
            raise NetworkLoadError([f"{path.name}: expected exactly one file in zip, "
                                    f"found {len(names)}: {names[:5]}"])
        return io.TextIOWrapper(zf.open(names[0]), encoding="utf-8", newline="")
    return path.open("r", encoding="utf-8", newline="")


def _rows(fh: io.TextIOBase, delimiter: str) -> Iterator[tuple[int, list[str]]]:
    reader = csv.reader(fh, delimiter=delimiter, quoting=csv.QUOTE_NONE)
    for i, row in enumerate(reader, start=1):
        if row:
            yield i, row


# --------------------------------------------------------------------------- STRING
def _dominant_evidence(channels: dict[str, int]) -> str:
    best, best_score = "predicted", 0
    for ch in _EVIDENCE_PRIORITY:
        if channels.get(ch, 0) > best_score:
            best, best_score = _CHANNEL_EVIDENCE[ch], channels[ch]
    return best


def load_string_links(path: str | Path, *, source_version: str,
                      min_combined_score: int = 700, taxon_id: int | None = None,
                      id_normalizer: IdNormalizer = default_gene_id,
                      max_reported_errors: int = 10) -> tuple[nx.MultiGraph, dict]:
    """Load ``protein.links[.detailed].vX.txt[.gz]`` (space separated, scores 0-1000).

    ``confidence`` = combined_score / 1000. The edge ``evidence_type`` is the dominant
    evidence *channel* among experimental/database/textmining (``predicted`` when none of
    these has a non-zero score or when only combined_score is available); all channel
    scores are stored as edge attributes (``score_<channel>``). A STRING combined score is
    an association confidence, not proof of a physical interaction.
    """
    if not 0 <= min_combined_score <= 1000:
        raise ValueError("min_combined_score must be in [0, 1000].")
    path = Path(path)
    errors: list[str] = []
    pairs: dict[tuple[str, str], dict[str, int]] = {}
    n_rows = n_below = n_self = n_merged = n_other_taxon = 0
    header: list[str] | None = None
    with _open_text(path) as fh:
        for lineno, row in _rows(fh, " "):
            if header is None:
                header = row
                need = {"protein1", "protein2", "combined_score"}
                if not need <= set(header):
                    raise NetworkLoadError([f"header lacks {sorted(need - set(header))}; "
                                            f"found {header[:10]}"])
                idx = {name: header.index(name) for name in header}
                continue
            if len(row) != len(header):
                errors.append(f"line {lineno}: expected {len(header)} fields, got {len(row)}")
                if len(errors) >= max_reported_errors:
                    break
                continue
            n_rows += 1
            try:
                scores = {name: int(row[idx[name]]) for name in
                          ("combined_score", *[c for c in STRING_CHANNELS if c in idx])}
            except ValueError:
                errors.append(f"line {lineno}: non-integer score")
                if len(errors) >= max_reported_errors:
                    break
                continue
            if any(not 0 <= v <= 1000 for v in scores.values()):
                errors.append(f"line {lineno}: score outside [0, 1000]")
                if len(errors) >= max_reported_errors:
                    break
                continue
            p1, p2 = row[idx["protein1"]], row[idx["protein2"]]
            if taxon_id is not None and not (p1.startswith(f"{taxon_id}.")
                                             and p2.startswith(f"{taxon_id}.")):
                n_other_taxon += 1
                continue
            if scores["combined_score"] < min_combined_score:
                n_below += 1
                continue
            a, b = id_normalizer(p1), id_normalizer(p2)
            if not a or not b:
                errors.append(f"line {lineno}: identifier normalised to empty string")
                if len(errors) >= max_reported_errors:
                    break
                continue
            if a == b:
                n_self += 1  # isoforms of one gene
                continue
            key = (a, b) if a < b else (b, a)
            if key in pairs:  # reverse direction row, or another isoform pair
                n_merged += 1
                prev = pairs[key]
                for name, val in scores.items():
                    prev[name] = max(prev.get(name, 0), val)
            else:
                pairs[key] = scores
    if header is None:
        raise NetworkLoadError(["empty file"])
    if errors:
        raise NetworkLoadError(errors)

    g: nx.MultiGraph = nx.MultiGraph()
    for (a, b), sc in sorted(pairs.items()):
        add_edge(g, a, b, source_db="STRING", source_version=source_version,
                 interaction_type="functional_association",
                 evidence_type=_dominant_evidence(sc),
                 confidence=sc["combined_score"] / 1000.0,
                 attributes={f"score_{k}": v for k, v in sc.items()})
    report = {"source_db": "STRING", "source_version": source_version, "path": str(path),
              "n_rows_read": n_rows, "n_edges": g.number_of_edges(),
              "n_nodes": g.number_of_nodes(), "n_below_threshold": n_below,
              "n_self_pairs_after_normalisation": n_self,
              "n_rows_merged_as_duplicates": n_merged, "n_other_taxon_skipped": n_other_taxon,
              "min_combined_score": min_combined_score, "channels_in_file":
              [c for c in STRING_CHANNELS if c in idx],
              "note": "Association confidence, not proof of physical interaction."}
    return g, report


# --------------------------------------------------------------------------- BioGRID
def load_biogrid_tab3(path: str | Path, *, source_version: str,
                      taxon_id: int | None = CHLAMYDOMONAS_TAXON_ID,
                      id_column: str = "Systematic Name",
                      id_normalizer: IdNormalizer = identity_id,
                      max_reported_errors: int = 10) -> tuple[nx.MultiGraph, dict]:
    """Load a BioGRID ``BIOGRID-*.tab3.txt`` (tab separated; plain, .gz or single-file .zip).

    ``id_column`` is ``"Systematic Name"`` or ``"Official Symbol"``. Rows with a missing
    identifier ('-' or empty) are counted, not guessed. One edge per (pair, physical|genetic);
    BioGRID interaction IDs are accumulated in ``evidence_ids``. ``taxon_id=None`` keeps all
    organisms (and requires A and B to be the same organism).
    """
    if id_column not in {"Systematic Name", "Official Symbol"}:
        raise ValueError("id_column must be 'Systematic Name' or 'Official Symbol'.")
    path = Path(path)
    col_a, col_b = f"{id_column} Interactor A", f"{id_column} Interactor B"
    errors: list[str] = []
    acc: dict[tuple[str, str, str], list[str]] = {}
    n_rows = n_missing_id = n_self = n_filtered = 0
    header: list[str] | None = None
    with _open_text(path) as fh:
        for lineno, row in _rows(fh, "\t"):
            if header is None:
                header = row
                missing = [c for c in BIOGRID_REQUIRED_COLUMNS if c not in header]
                if col_a not in header or col_b not in header:
                    missing += [c for c in (col_a, col_b) if c not in header]
                if missing:
                    raise NetworkLoadError([f"BioGRID header lacks {sorted(set(missing))}; "
                                            "is this a TAB3 file?"])
                idx = {name: header.index(name) for name in header}
                continue
            if len(row) != len(header):
                errors.append(f"line {lineno}: expected {len(header)} fields, got {len(row)}")
                if len(errors) >= max_reported_errors:
                    break
                continue
            n_rows += 1
            org_a, org_b = row[idx["Organism ID Interactor A"]], row[idx["Organism ID Interactor B"]]
            if taxon_id is None:
                if org_a != org_b:
                    n_filtered += 1
                    continue
            elif org_a != str(taxon_id) or org_b != str(taxon_id):
                n_filtered += 1
                continue
            raw_a, raw_b = row[idx[col_a]].strip(), row[idx[col_b]].strip()
            if raw_a in {"", "-"} or raw_b in {"", "-"}:
                n_missing_id += 1
                continue
            a, b = id_normalizer(raw_a), id_normalizer(raw_b)
            if a == b:
                n_self += 1
                continue
            itype = row[idx["Experimental System Type"]].strip().lower()
            if itype not in {"physical", "genetic"}:
                errors.append(f"line {lineno}: Experimental System Type {itype!r} "
                              "is not physical/genetic")
                if len(errors) >= max_reported_errors:
                    break
                continue
            key = (a, b, itype) if a < b else (b, a, itype)
            ids = acc.setdefault(key, [])
            iid = row[idx["#BioGRID Interaction ID"]].strip()
            if iid and iid not in ids:
                ids.append(iid)
    if header is None:
        raise NetworkLoadError(["empty file"])
    if errors:
        raise NetworkLoadError(errors)

    g: nx.MultiGraph = nx.MultiGraph()
    for (a, b, itype), ids in sorted(acc.items()):
        add_edge(g, a, b, source_db="BioGRID", source_version=source_version,
                 interaction_type=itype, evidence_type="experimental", confidence=None,
                 evidence_ids=ids)
    report = {"source_db": "BioGRID", "source_version": source_version, "path": str(path),
              "taxon_id": taxon_id, "id_column": id_column, "n_rows_read": n_rows,
              "n_edges": g.number_of_edges(), "n_nodes": g.number_of_nodes(),
              "n_filtered_other_organism": n_filtered, "n_missing_identifier": n_missing_id,
              "n_self_pairs": n_self,
              "note": "Experimental evidence per curated record; no confidence score reported."}
    return g, report


# --------------------------------------------------------------------------- utilities
def merge_graphs(*graphs: nx.MultiGraph) -> nx.MultiGraph:
    """Union of provenance-tagged graphs. Edge keys include the source database, so STRING and
    BioGRID edges between the same genes coexist; an identical key twice is an error."""
    out: nx.MultiGraph = nx.MultiGraph()
    for g in graphs:
        for a, b, key, data in g.edges(keys=True, data=True):
            if out.has_edge(a, b, key):
                raise ValueError(f"Duplicate edge {a}-{b} for {key}; load each source once.")
            out.add_edge(a, b, key=key, **data)
    return out


def expression_overlap(g: nx.MultiGraph, gene_ids, example_limit: int = 5) -> dict:
    """How many network nodes appear in the expression matrix. A low fraction almost always
    means an identifier/genome-version mismatch, not an absence of biology."""
    genes = set(map(str, gene_ids))
    nodes = set(g.nodes)
    hit = nodes & genes
    return {"n_network_nodes": len(nodes), "n_expression_genes": len(genes),
            "n_nodes_in_expression": len(hit),
            "fraction_nodes_in_expression": (len(hit) / len(nodes)) if nodes else None,
            "fraction_expression_genes_in_network": (len(hit) / len(genes)) if genes else None,
            "unmatched_node_examples": sorted(nodes - genes)[:example_limit],
            "unmatched_expression_examples": sorted(genes - nodes)[:example_limit]}


def restrict_to_genes(g: nx.MultiGraph, gene_ids) -> nx.MultiGraph:
    """Induced subgraph on genes present in the expression data (copy; provenance kept)."""
    keep = set(map(str, gene_ids)) & set(g.nodes)
    return nx.MultiGraph(g.subgraph(keep))
