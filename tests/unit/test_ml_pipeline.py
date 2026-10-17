"""ML pipeline tests. All data are SYNTHETIC (software mechanics only)."""
import numpy as np
import pytest

from app.ml import pipeline as p


@pytest.fixture(scope="module")
def df():
    return p.make_demo_dataset()


def test_grouped_split_has_no_group_overlap(df):
    cfg = p.TrainConfig()
    tr, va, te = p.grouped_split(df, cfg)
    g = df["group"].to_numpy()
    assert not (set(g[tr]) & set(g[va]))
    assert not (set(g[tr]) & set(g[te]))
    assert not (set(g[va]) & set(g[te]))
    assert len(set(tr) | set(va) | set(te)) == len(df)


def test_validation_rejects_bad_targets(df):
    cfg = p.TrainConfig()
    with pytest.raises(ValueError, match="single class"):
        p.validate_training_frame(df.assign(label=0), cfg)
    with pytest.raises(ValueError, match="binary"):
        p.validate_training_frame(df.assign(label=df["label"] + 1), cfg)
    with pytest.raises(ValueError, match="not found"):
        p.validate_training_frame(df.drop(columns="label"), cfg)
    with pytest.raises(ValueError, match="min_per_class"):
        rare = df.copy()
        rare["label"] = 0
        rare.loc[rare.index[:2], "label"] = 1
        p.validate_training_frame(rare, cfg)


def test_metrics_return_none_when_undefined():
    m = p.classification_metrics([0, 0, 0], [0.1, 0.2, 0.3], 0.5)
    assert m["roc_auc"] is None and m["average_precision"] is None
    assert m["recall_sensitivity"] is None  # no positives: undefined, not 0


def test_train_save_load_predict_roundtrip(df, tmp_path):
    cfg = p.TrainConfig(synthetic=True)
    rep = p.train_and_evaluate(df, cfg, out_dir=tmp_path)
    assert rep["selected_model"] != "dummy_prior"
    assert any("SYNTHETIC" in c for c in rep["caveats"])
    feats = [c for c in df.columns if c.startswith("f")]
    out = p.predict(tmp_path, df[feats].head(4).to_dict("records"))
    assert len(out["predictions"]) == 4
    assert out["calibrated"] is False and out["synthetic_training_data"] is True
    assert all(0 <= r["score"] <= 1 for r in out["predictions"])


def test_training_is_deterministic(df):
    a = p.train_and_evaluate(df, p.TrainConfig())
    b = p.train_and_evaluate(df, p.TrainConfig())
    assert a["test_metrics"] == b["test_metrics"]


def test_prediction_validates_features(df, tmp_path):
    p.train_and_evaluate(df, p.TrainConfig(synthetic=True), out_dir=tmp_path)
    feats = [c for c in df.columns if c.startswith("f")]
    rec = df[feats].iloc[0].to_dict()
    with pytest.raises(p.FeatureValidationError, match="missing"):
        p.predict(tmp_path, [{"f0": 1.0}])
    with pytest.raises(p.FeatureValidationError, match="unexpected"):
        p.predict(tmp_path, [{**rec, "extra": 1.0}])
    with pytest.raises(p.FeatureValidationError, match="non-numeric"):
        p.predict(tmp_path, [{**rec, "f0": "abc"}])
    with pytest.raises(p.FeatureValidationError, match="infinite"):
        p.predict(tmp_path, [{**rec, "f0": np.inf}])


def test_missing_and_tampered_artifacts_are_reported(df, tmp_path):
    with pytest.raises(p.ModelArtifactError, match="no model artifact"):
        p.load_artifact(tmp_path / "absent")
    p.train_and_evaluate(df, p.TrainConfig(synthetic=True), out_dir=tmp_path)
    model = tmp_path / p.MODEL_FILE
    model.write_bytes(model.read_bytes() + b"x")
    with pytest.raises(p.ModelArtifactError, match="checksum"):
        p.load_artifact(tmp_path)
