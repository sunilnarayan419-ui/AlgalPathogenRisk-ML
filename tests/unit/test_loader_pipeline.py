"""All data here is SYNTHETIC and is not biological evidence."""
import gzip

import numpy as np
import pandas as pd
import pytest

from app.analysis.pipeline import run_exploratory
from app.data.loader import FpkmValidationError, load_fpkm


def _frame(n_genes=60, n_samples=6, seed=0):
    rng = np.random.default_rng(seed)
    cols = [f"S{i}" for i in range(n_samples)]
    df = pd.DataFrame(rng.gamma(2, 5, (n_genes, n_samples)), columns=cols)
    df.insert(0, "gene", [f"g{i}" for i in range(n_genes)])
    return df


def test_valid_gz_loads_with_checksum(tmp_path):
    p = tmp_path / "f.tsv.gz"
    _frame().to_csv(p, sep="\t", index=False)
    df, rep = load_fpkm(p, expected_samples=6)
    assert df.shape == (60, 6) and len(rep["sha256"]) == 64 and rep["unit"].startswith("FPKM")




def _bad(tmp_path, edit):
    df = _frame()
    edit(df)
    p = tmp_path / "b.tsv"
    df.to_csv(p, sep="\t", index=False)
    return p


def test_rejections(tmp_path):
    cases = {
        "negative": lambda d: d.__setitem__("S0", d["S0"].where(d.index != 0, -1.0)),
        "duplicated gene": lambda d: d.__setitem__("gene", ["g0"] * 2 + list(d["gene"][2:])),
        "blank gene": lambda d: d.__setitem__("gene", [""] + list(d["gene"][1:])),
        "non-numeric": lambda d: d.__setitem__("S1", d["S1"].astype(object).where(d.index != 0, "abc")),
        "infinite": lambda d: d.__setitem__("S2", d["S2"].where(d.index != 0, np.inf)),
    }
    for needle, edit in cases.items():
        with pytest.raises(FpkmValidationError):
            load_fpkm(_bad(tmp_path, edit))


def test_missing_file_wrong_count_and_corrupt_gzip(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_fpkm(tmp_path / "nope.tsv")
    p = tmp_path / "f.tsv"
    _frame().to_csv(p, sep="\t", index=False)
    with pytest.raises(FpkmValidationError):
        load_fpkm(p, expected_samples=21)
    g = tmp_path / "x.tsv.gz"
    g.write_bytes(gzip.compress(b"a\tb\n1\t2\n")[:-5])
    with pytest.raises(FpkmValidationError):
        load_fpkm(g)


def test_pipeline_outputs_and_metadata_mismatch(tmp_path):
    p = tmp_path / "f.tsv"
    df = _frame()
    df.to_csv(p, sep="\t", index=False)
    cols = [c for c in df.columns if c != "gene"]
    meta = tmp_path / "m.csv"
    pd.DataFrame({"sample_id": cols, "group": ["A", "A", "A", "B", "B", "B"]}).to_csv(meta, index=False)
    s = run_exploratory(p, tmp_path / "out", meta)
    assert (tmp_path / "out" / "pca.png").exists() and s["transform"]["pseudocount"] == 1.0
    assert s["groups_provided"] is True
    pd.DataFrame({"sample_id": cols[:-1], "group": ["A"] * 5}).to_csv(meta, index=False)
    with pytest.raises(ValueError):
        run_exploratory(p, tmp_path / "out2", meta)
