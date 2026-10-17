"""Write a SYNTHETIC FPKM-like table using the GSE128981 sample layout (software tests only).

Values are random draws, not measurements. A 'true effect' is planted in the first genes for
strain UVM4 so DE code can be checked; this says nothing about the real biology.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.metadata import audit_geo_series_matrix, build_sample_manifest  # noqa: E402


def make(series_matrix: Path, out_fpkm: Path, n_genes: int = 300, seed: int = 7) -> None:
    man = build_sample_manifest(audit_geo_series_matrix(series_matrix), gse128981_batch_rule=True)
    rng = np.random.default_rng(seed)
    base = rng.gamma(2.0, 8.0, size=(n_genes, 1))
    data = base * rng.lognormal(0, 0.25, size=(n_genes, len(man)))
    data[man["batch"].eq("batch2").to_numpy()[None, :].repeat(n_genes, 0)] *= 1.15  # batch shift
    data[:15, man["strain"].eq("UVM4").to_numpy()] *= 6.0                           # planted effect
    df = pd.DataFrame(data, columns=man["sample_accession"],
                      index=[f"SYN{i:04d}" for i in range(n_genes)])
    df.index.name = "gene_id"
    out_fpkm.parent.mkdir(parents=True, exist_ok=True)
    df.round(4).to_csv(out_fpkm, sep="\t")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    make(root / "tests/fixtures/GSE128981_series_matrix.txt",
         root / "tests/fixtures/SYNTHETIC_fpkm_gse128981_layout.tsv")
