import gzip
import re
from pathlib import Path

import pandas as pd


def _read_text(path: Path) -> str:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    return path.read_text(encoding="utf-8", errors="replace")

def audit_geo_series_matrix(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        return {"exists": False, "path": str(path), "error": "File not found"}
    lines = _read_text(path).splitlines()
    title = accession = None
    sample_titles, sample_ids = [], []
    table_begin = table_end = False
    in_table, table_rows = False, 0
    characteristics: list[list[str]] = []
    sample_fields: dict[str, list[list[str]]] = {}
    overall_design = None
    for line in lines:
        if in_table and not line.startswith("!series_matrix_table_end"):
            table_rows += 1  # first row is the header; counted off below
        if line.startswith("!Sample_") and "\t" in line:
            sample_fields.setdefault(line.split("\t", 1)[0], []).append(
                [v.strip().strip('"') for v in line.split("\t")[1:]])
        if line.startswith("!Series_overall_design"):
            overall_design = line.split("\t", 1)[-1].strip().strip('"')
        if line.startswith("!Sample_characteristics_ch1"):
            characteristics.append([v.strip().strip('"') for v in line.split("\t")[1:]])
        if line.startswith("!Series_title"):
            title = line.split("\t", 1)[-1].strip().strip('"')
        elif line.startswith("!Series_geo_accession"):
            accession = line.split("\t", 1)[-1].strip().strip('"')
        elif line.startswith("!Sample_title"):
            sample_titles = [v.strip().strip('"') for v in line.split("\t")[1:]]
        elif line.startswith("!Sample_geo_accession"):
            sample_ids = [v.strip().strip('"') for v in line.split("\t")[1:]]
        elif line.startswith("!series_matrix_table_begin"):
            table_begin = True
            in_table = True
        elif line.startswith("!series_matrix_table_end"):
            table_end = True
            in_table = False
    return {
        "exists": True, "path": str(path), "accession": accession, "title": title,
        "sample_count_from_titles": len(sample_titles),
        "sample_count_from_accessions": len(sample_ids),
        "sample_titles": sample_titles, "sample_accessions": sample_ids,
        "expression_table_markers_present": table_begin and table_end,
        "expression_matrix_has_gene_rows": max(table_rows - 1, 0) > 0,
        "expression_table_gene_rows": max(table_rows - 1, 0),
        "sample_characteristics_ch1": characteristics,
        "sample_fields": sample_fields, "series_overall_design": overall_design,
        "interpretation": "Inspect/download the supplementary FPKM matrix before expression-level modelling."
    }

def load_expression_matrix(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path, sep="\t", index_col=0, compression="infer")
    if frame.empty:
        raise ValueError("Expression matrix is empty.")
    if frame.index.has_duplicates or frame.columns.has_duplicates:
        raise ValueError("Duplicate gene identifiers or sample identifiers found.")
    frame = frame.apply(pd.to_numeric, errors="raise")
    if frame.isna().any().any():
        raise ValueError("Expression matrix contains missing values.")
    return frame


# --- Sample manifest ------------------------------------------------------------------

_UNRESOLVED = "unresolved"
# Series-specific rule for GSE128981 only. The GEO text says the study ran in two batches
# (batch 1: Elow47/UVM4/UVM11 reps 1-4; batch 2: UVM11 repeated, UVM11-C1, UVM11-C9) but no
# per-sample batch field exists; this maps the two accession blocks to those batches. Confirm
# against the paper's supplement before relying on it.
GSE128981_BATCH_BLOCKS = {"batch1": (3689501, 3689512), "batch2": (4733487, 4733495)}


def infer_batch_gse128981(gsm: str) -> str:
    m = re.fullmatch(r"GSM(\d+)", gsm)
    if m:
        n = int(m.group(1))
        for label, (lo, hi) in GSE128981_BATCH_BLOCKS.items():
            if lo <= n <= hi:
                return label
    return _UNRESOLVED


def _characteristics(audit: dict, n: int) -> list[dict[str, str]]:
    out: list[dict[str, str]] = [{} for _ in range(n)]
    for row in audit["sample_characteristics_ch1"]:
        for i, cell in enumerate(row[:n]):
            if ":" in cell:
                k, v = cell.split(":", 1)
                out[i][k.strip()] = v.strip()
    return out


def build_sample_manifest(audit: dict, gse128981_batch_rule: bool = False) -> pd.DataFrame:
    """One row per sample from parsed GEO metadata; absent fields are 'unresolved', never guessed."""
    ids = audit["sample_accessions"]
    titles = audit["sample_titles"]
    if len(ids) != len(titles) or not ids:
        raise ValueError("Sample accessions and titles are missing or differ in length.")
    chars = _characteristics(audit, len(ids))
    fields = audit.get("sample_fields", {})

    def first(name: str) -> list[str]:
        rows = fields.get(name, [])
        return rows[0] if rows else [_UNRESOLVED] * len(ids)

    rows = []
    for i, gsm in enumerate(ids):
        rep = re.search(r"rep(\d+)\s*$", titles[i])
        batch = infer_batch_gse128981(gsm) if gse128981_batch_rule else _UNRESOLVED
        rows.append({
            "sample_accession": gsm, "title": titles[i],
            "strain": chars[i].get("strain", _UNRESOLVED),
            "genotype": chars[i].get("genotype", _UNRESOLVED),
            "replicate_in_title": int(rep.group(1)) if rep else _UNRESOLVED,
            "batch": batch,
            "batch_source": ("inferred: accession block + series overall_design text"
                             if batch != _UNRESOLVED else _UNRESOLVED),
            "growth_condition": first("!Sample_growth_protocol_ch1")[i],
            "treatment": first("!Sample_treatment_protocol_ch1")[i],
            "instrument": first("!Sample_instrument_model")[i],
        })
    m = pd.DataFrame(rows)
    if m["sample_accession"].duplicated().any():
        raise ValueError("Duplicate sample accessions in metadata.")
    return m
