import numpy as np
import pandas as pd
import pytest

from app.data.counts import CountsValidationError, align_metadata, load_counts


def _tsv(tmp_path, df, name="c.tsv"):
    p = tmp_path / name
    df.to_csv(p, sep="\t")
    return p


def _counts():
    return pd.DataFrame({"s1": [10, 0, 5], "s2": [12, 1, 7], "s3": [9, 0, 6]},
                        index=pd.Index(["g1", "g2", "g3"], name="gene_id"))


def test_load_valid_counts(tmp_path):
    df, rep = load_counts(_tsv(tmp_path, _counts()))
    assert df.shape == (3, 3) and str(df.dtypes.iloc[0]) == "int64"
    assert rep["unit"].startswith("raw counts") and rep["all_zero_genes"] == 0


@pytest.mark.parametrize("mutate", [
    lambda d: d.astype(float) + 0.5,                       # looks like normalised data
    lambda d: d.mask(d == 5, -5),                          # negative
    lambda d: d.astype(object).mask(d == 5, "NA"),         # non-numeric
])
def test_rejects_bad_counts(tmp_path, mutate):
    with pytest.raises(CountsValidationError):
        load_counts(_tsv(tmp_path, mutate(_counts())))


def test_rejects_duplicate_genes_and_infinite(tmp_path):
    dup = pd.concat([_counts(), _counts().iloc[[0]]])
    with pytest.raises(CountsValidationError):
        load_counts(_tsv(tmp_path, dup))
    inf = _counts().astype(float)
    inf.iloc[0, 0] = np.inf
    with pytest.raises(CountsValidationError):
        load_counts(_tsv(tmp_path, inf, "inf.tsv"))


def test_round_noninteger_and_sample_map(tmp_path):
    est = _counts().astype(float) + 0.3
    with pytest.raises(CountsValidationError):
        load_counts(_tsv(tmp_path, est))
    df, rep = load_counts(_tsv(tmp_path, est), round_noninteger=True)
    assert rep["n_noninteger_rounded"] == 9 and (df.to_numpy() == np.round(est.to_numpy())).all()
    df, _ = load_counts(_tsv(tmp_path, _counts()), sample_map={"s1": "A", "s2": "B", "s3": "C"})
    assert list(df.columns) == ["A", "B", "C"]
    with pytest.raises(CountsValidationError):                       # unmapped column
        load_counts(_tsv(tmp_path, _counts()), sample_map={"s1": "A"})
    with pytest.raises(CountsValidationError):                       # duplicate targets
        load_counts(_tsv(tmp_path, _counts()), sample_map={"s1": "A", "s2": "A", "s3": "C"})


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_counts(tmp_path / "nope.tsv")


def test_align_metadata():
    counts, _ = _counts(), None
    meta = pd.DataFrame({"sample_id": ["s3", "s1", "s2"], "group": ["a", "a", "b"]})
    out = align_metadata(counts, meta)
    assert list(out.index) == ["s1", "s2", "s3"]
    with pytest.raises(ValueError):
        align_metadata(counts, meta.iloc[:2])                         # sample missing
    with pytest.raises(ValueError):
        align_metadata(counts, meta.assign(group=["a", "", "b"]))     # blank group
    with pytest.raises(ValueError):
        align_metadata(counts, pd.concat([meta, meta.iloc[[0]]]))     # duplicate id
    with pytest.raises(ValueError):
        align_metadata(counts, meta, required=("group", "batch"))     # missing column
