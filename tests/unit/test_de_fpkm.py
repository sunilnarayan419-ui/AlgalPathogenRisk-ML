"""Differential-expression tests on SYNTHETIC data."""
import numpy as np
import pandas as pd
import pytest
from scipy import stats

from app.analysis.de_fpkm import differential_expression_log2 as de
from app.experiments.analysis import benjamini_hochberg
from app.experiments.count_de import ConfoundingError, DesignError


@pytest.fixture(scope="module")
def data():
    rng = np.random.default_rng(1)
    cols = [f"A{i}" for i in range(4)] + [f"B{i}" for i in range(4)]
    X = pd.DataFrame(rng.gamma(2, 10, (200, 8)), index=[f"g{i}" for i in range(200)], columns=cols)
    X.iloc[:10, :4] *= 8
    meta = pd.DataFrame({"grp": ["a"] * 4 + ["b"] * 4,
                         "batch": ["1", "1", "2", "2", "1", "1", "2", "2"]}, index=cols)
    return X, meta


def test_matches_student_t_test(data):
    X, meta = data
    res, rep = de(X, meta, "grp", "a", "b")
    y = np.log2(X + 1)
    t = stats.ttest_ind(y.loc["g0", :].iloc[:4], y.loc["g0", :].iloc[4:], equal_var=True)
    assert np.isclose(res.loc["g0", "p_value"], t.pvalue) and np.isclose(res.loc["g0", "t"], t.statistic)
    assert rep["df_residual"] == 6 and not rep["batch_adjusted"]


def test_output_schema_and_bh(data):
    X, meta = data
    res, _ = de(X, meta, "grp", "a", "b")
    assert {"log2_diff_a_minus_b", "ci_low", "ci_high", "p_value", "padj_bh", "hedges_g"} <= set(res.columns)
    ok = res["p_value"].notna()
    assert np.allclose(res.loc[ok, "padj_bh"].sort_index(),
                       benjamini_hochberg(res.loc[ok, "p_value"].sort_index().to_numpy()))
    assert (res["ci_low"] <= res["log2_diff_a_minus_b"]).all()
    rank = pd.Series(range(len(res)), index=res.index)
    assert rank[[f"g{i}" for i in range(10)]].median() < rank.median() / 3


def test_batch_adjustment_and_confounding(data):
    X, meta = data
    _, rep = de(X, meta, "grp", "a", "b", batch_col="batch")
    assert rep["batch_adjusted"] and rep["df_residual"] == 5
    conf = meta.assign(batch=["1"] * 4 + ["2"] * 4)
    with pytest.raises(ConfoundingError):
        de(X, conf, "grp", "a", "b", batch_col="batch")
    _, rep2 = de(X, conf, "grp", "a", "b", batch_col="batch", allow_unadjusted=True)
    assert "batch_confounded" in rep2["flags"]


def test_input_guards(data):
    X, meta = data
    with pytest.raises(DesignError):
        de(X, meta, "grp", "a", "zzz")
    with pytest.raises(DesignError, match="per group"):
        de(X, meta.assign(grp=["a"] + ["c"] * 3 + ["b"] * 4), "grp", "a", "c", min_replicates=2)
    with pytest.raises(ValueError, match="non-negative"):
        de(X - 1000, meta, "grp", "a", "b")
    with pytest.raises(ValueError, match="differ"):
        de(X, meta, "grp", "a", "a")
