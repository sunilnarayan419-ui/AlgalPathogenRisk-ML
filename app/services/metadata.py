from pathlib import Path
import pandas as pd

def audit_geo_series_matrix(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        return {"exists": False, "path": str(path), "error": "File not found"}
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    title = accession = None
    sample_titles, sample_ids = [], []
    table_begin = table_end = False
    for line in lines:
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
        elif line.startswith("!series_matrix_table_end"):
            table_end = True
    return {
        "exists": True, "path": str(path), "accession": accession, "title": title,
        "sample_count_from_titles": len(sample_titles),
        "sample_count_from_accessions": len(sample_ids),
        "sample_titles": sample_titles, "sample_accessions": sample_ids,
        "expression_table_markers_present": table_begin and table_end,
        "expression_matrix_has_gene_rows": False,
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
