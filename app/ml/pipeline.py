"""Leakage-safe train / evaluate / persist / predict pipeline for tabular binary targets.

SCIENTIFIC STATUS
-----------------
GSE128981 has no infection or culture-collapse labels, so this module is NOT used to
produce pathogen-risk predictions from it. It is generic software that trains on any
labelled table the caller supplies. ``make_demo_dataset`` produces SYNTHETIC data for
exercising the software only; artifacts trained on it are flagged ``synthetic=True`` and
their scores must never be read as biological evidence or real-world performance.

Design rules
------------
* All preprocessing (imputation, scaling) lives inside the sklearn Pipeline, so it is
  fit on training folds only.
* Splits are group-aware: samples sharing a group id (e.g. replicates of one culture)
  are never split across train/validation/test.
* The decision threshold is chosen on validation data, never on the held-out test set.
* Scores are uncalibrated unless a calibration step is explicitly recorded; predictions
  always say so.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ARTIFACT_FORMAT_VERSION = 1
MODEL_FILE = "model.joblib"
META_FILE = "metadata.json"

CALIBRATION_NOTE = (
    "Scores are uncalibrated model outputs, not validated probabilities of pathogen "
    "infection or culture collapse. No external validation has been performed."
)
SYNTHETIC_NOTE = (
    "Trained on SYNTHETIC demonstration data. Metrics show that the software runs; "
    "they are not biological evidence."
)


class ModelArtifactError(RuntimeError):
    """Missing, corrupt or incompatible model artifact."""


class FeatureValidationError(ValueError):
    """Inference input does not match the training feature schema."""


@dataclass(frozen=True)
class TrainConfig:
    target: str = "label"
    group_column: str | None = "group"
    seed: int = 42
    test_size: float = 0.25
    val_size: float = 0.25
    cv_splits: int = 3
    min_per_class: int = 5
    selection_metric: str = "average_precision"  # chosen on validation data only
    threshold_criterion: str = "max_f1_on_validation"
    synthetic: bool = False


# --------------------------------------------------------------------------- demo data
def make_demo_dataset(n_groups: int = 60, reps: int = 2, n_features: int = 8,
                      prevalence: float = 0.3, seed: int = 42) -> pd.DataFrame:
    """SYNTHETIC data for software tests only. Label depends on two features + noise."""
    rng = np.random.default_rng(seed)
    rows = []
    for g in range(n_groups):
        y = int(rng.random() < prevalence)
        base = rng.normal(0, 1, n_features)
        base[0] += 1.5 * y
        base[1] -= 1.0 * y
        for _ in range(reps):  # replicates share a group id -> must not leak across splits
            rows.append({**{f"f{i}": base[i] + rng.normal(0, 0.3) for i in range(n_features)},
                         "group": f"g{g}", "label": y})
    df = pd.DataFrame(rows)
    df.attrs["synthetic"] = True
    return df


# --------------------------------------------------------------------------- validation
def validate_training_frame(df: pd.DataFrame, cfg: TrainConfig) -> list[str]:
    """Return the feature columns after checking labels, groups and dtypes."""
    if cfg.target not in df.columns:
        raise ValueError(f"target column {cfg.target!r} not found.")
    if cfg.group_column is not None and cfg.group_column not in df.columns:
        raise ValueError(f"group column {cfg.group_column!r} not found; pass group_column=None "
                         "only if samples are independent.")
    y = df[cfg.target]
    if y.isna().any():
        raise ValueError("target contains missing values.")
    if set(pd.unique(y)) - {0, 1}:
        raise ValueError("target must be binary 0/1.")
    counts = y.value_counts()
    if len(counts) < 2:
        raise ValueError("target has a single class.")
    if counts.min() < cfg.min_per_class:
        raise ValueError(f"smallest class has {int(counts.min())} samples "
                         f"(< min_per_class={cfg.min_per_class}); refusing to train.")
    features = [c for c in df.columns if c not in {cfg.target, cfg.group_column}]
    if not features:
        raise ValueError("no feature columns.")
    non_numeric = [c for c in features if not pd.api.types.is_numeric_dtype(df[c])]
    if non_numeric:
        raise ValueError(f"non-numeric feature columns: {non_numeric[:5]}")
    if np.isinf(df[features].to_numpy(float)).any():
        raise ValueError("features contain infinite values.")
    return features


def grouped_split(df: pd.DataFrame, cfg: TrainConfig) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Train/validation/test row indices; no group appears in more than one part."""
    groups = (df[cfg.group_column].to_numpy() if cfg.group_column
              else np.arange(len(df)))
    idx = np.arange(len(df))
    outer = GroupShuffleSplit(n_splits=1, test_size=cfg.test_size, random_state=cfg.seed)
    trainval, test = next(outer.split(idx, groups=groups))
    inner = GroupShuffleSplit(n_splits=1, test_size=cfg.val_size / (1 - cfg.test_size),
                              random_state=cfg.seed)
    tr_rel, va_rel = next(inner.split(trainval, groups=groups[trainval]))
    train, val = trainval[tr_rel], trainval[va_rel]
    for a, b in ((train, val), (train, test), (val, test)):
        if set(groups[a]) & set(groups[b]):  # defensive: should be impossible
            raise AssertionError("group leakage between splits")
    return train, val, test


# --------------------------------------------------------------------------- models
def candidate_models(seed: int) -> dict[str, Pipeline]:
    imp = lambda: ("impute", SimpleImputer(strategy="median"))  # noqa: E731
    return {
        "dummy_prior": Pipeline([("clf", DummyClassifier(strategy="prior"))]),
        "logistic_l2": Pipeline([imp(), ("scale", StandardScaler()),
                                 ("clf", LogisticRegression(C=0.5, max_iter=5000,
                                                            class_weight="balanced",
                                                            random_state=seed))]),
        "random_forest": Pipeline([imp(), ("clf", RandomForestClassifier(
            n_estimators=300, min_samples_leaf=2, class_weight="balanced_subsample",
            random_state=seed, n_jobs=1))]),
        "hist_gradient_boosting": Pipeline([("clf", HistGradientBoostingClassifier(
            max_iter=150, learning_rate=0.05, random_state=seed))]),
    }


# --------------------------------------------------------------------------- metrics
def classification_metrics(y_true, score, threshold: float) -> dict[str, Any]:
    """Metrics that are undefined (single-class truth) are returned as None, never faked."""
    y_true = np.asarray(y_true).astype(int)
    score = np.asarray(score, dtype=float)
    pred = (score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    two_classes = len(np.unique(y_true)) == 2

    def ratio(a, b):
        return float(a / b) if b else None

    return {
        "n": int(len(y_true)), "n_positive": int(y_true.sum()), "threshold": float(threshold),
        "roc_auc": float(roc_auc_score(y_true, score)) if two_classes else None,
        "average_precision": float(average_precision_score(y_true, score)) if two_classes else None,
        "precision": ratio(tp, tp + fp), "recall_sensitivity": ratio(tp, tp + fn),
        "specificity": ratio(tn, tn + fp),
        "f1": float(f1_score(y_true, pred, zero_division=0)),
        "brier": float(brier_score_loss(y_true, score)),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def calibration_table(y_true, score, n_bins: int = 5) -> list[dict]:
    """Reliability diagnostics (quantile bins). Diagnostic only; with tiny n it is noisy."""
    df = pd.DataFrame({"y": np.asarray(y_true), "s": np.asarray(score, dtype=float)})
    try:
        df["bin"] = pd.qcut(df["s"], q=n_bins, duplicates="drop")
    except ValueError:
        return []
    g = df.groupby("bin", observed=True)
    return [{"mean_score": float(v["s"].mean()), "observed_rate": float(v["y"].mean()),
             "n": int(len(v))} for _, v in g]


def choose_threshold(y_val, score_val) -> float:
    """Documented criterion: threshold maximising F1 on the validation set."""
    cands = np.unique(np.round(np.asarray(score_val, dtype=float), 6))
    best_t, best_f1 = 0.5, -1.0
    for t in cands:
        f1 = f1_score(y_val, (score_val >= t).astype(int), zero_division=0)
        if f1 > best_f1:
            best_t, best_f1 = float(t), f1
    return best_t


def _positive_score(pipe: Pipeline, X: pd.DataFrame) -> np.ndarray:
    return pipe.predict_proba(X)[:, 1]


def _error_analysis(df: pd.DataFrame, test_idx, y_test, score, thr, cfg: TrainConfig) -> dict:
    pred = (np.asarray(score) >= thr).astype(int)
    ident = (df[cfg.group_column].to_numpy()[test_idx] if cfg.group_column
             else np.asarray(test_idx))
    fp = [str(i) for i in ident[(pred == 1) & (y_test == 0)]]
    fn = [str(i) for i in ident[(pred == 0) & (y_test == 1)]]
    return {"false_positive_units": sorted(set(fp)), "false_negative_units": sorted(set(fn)),
            "n_false_positive_rows": len(fp), "n_false_negative_rows": len(fn)}


# --------------------------------------------------------------------------- training
def train_and_evaluate(df: pd.DataFrame, cfg: TrainConfig, out_dir: str | Path | None = None,
                       dataset_provenance: dict | None = None) -> dict[str, Any]:
    """Train all candidates, select on validation, evaluate ONCE on test, optionally save."""
    features = validate_training_frame(df, cfg)
    train, val, test = grouped_split(df, cfg)
    X, y = df[features], df[cfg.target].to_numpy()
    for name, part in (("train", train), ("validation", val), ("test", test)):
        if len(np.unique(y[part])) < 2:
            raise ValueError(f"{name} split contains a single class; use more data or a "
                             "different seed/split sizes.")

    groups = df[cfg.group_column].to_numpy() if cfg.group_column else np.arange(len(df))
    cv = StratifiedGroupKFold(n_splits=cfg.cv_splits, shuffle=True, random_state=cfg.seed)
    results: dict[str, Any] = {}
    fitted: dict[str, Pipeline] = {}
    for name, pipe in candidate_models(cfg.seed).items():
        # cross-validation on the training portion only (groups kept together)
        cv_scores = []
        for tr_i, te_i in cv.split(X.iloc[train], y[train], groups[train]):
            m = candidate_models(cfg.seed)[name]
            tr_idx, te_idx = train[tr_i], train[te_i]
            if len(np.unique(y[te_idx])) < 2:
                continue
            m.fit(X.iloc[tr_idx], y[tr_idx])
            cv_scores.append(average_precision_score(y[te_idx], _positive_score(m, X.iloc[te_idx])))
        pipe.fit(X.iloc[train], y[train])
        s_val = _positive_score(pipe, X.iloc[val])
        thr = choose_threshold(y[val], s_val)
        results[name] = {
            "cv_average_precision_mean": float(np.mean(cv_scores)) if cv_scores else None,
            "cv_average_precision_sd": float(np.std(cv_scores, ddof=1)) if len(cv_scores) > 1 else None,
            "cv_folds_used": len(cv_scores),
            "validation": classification_metrics(y[val], s_val, thr),
            "threshold": thr,
        }
        fitted[name] = pipe

    non_dummy = [n for n in results if n != "dummy_prior"]
    best = max(non_dummy, key=lambda n: results[n]["validation"][cfg.selection_metric] or -1)
    best_pipe = fitted[best]
    thr = results[best]["threshold"]
    s_test = _positive_score(best_pipe, X.iloc[test])
    test_metrics = classification_metrics(y[test], s_test, thr)
    dummy_test = classification_metrics(
        y[test], _positive_score(fitted["dummy_prior"], X.iloc[test]),
        results["dummy_prior"]["threshold"])

    report = {
        "selected_model": best, "selection_metric": cfg.selection_metric,
        "threshold_criterion": cfg.threshold_criterion, "threshold": thr,
        "test_metrics": test_metrics, "dummy_baseline_test_metrics": dummy_test,
        "test_calibration_table": calibration_table(y[test], s_test),
        "test_errors": _error_analysis(df, test, y[test], s_test, thr, cfg),
        "dataset": {"n_rows": int(len(df)), "n_features": len(features), "features": features,
                    "target": cfg.target, "group_column": cfg.group_column,
                    "n_groups": int(len(set(groups))), "synthetic": cfg.synthetic,
                    "provenance": dataset_provenance or {}},
        "config": {k: getattr(cfg, k) for k in cfg.__dataclass_fields__},
        "candidates": results,
        "split_sizes": {"train": len(train), "validation": len(val), "test": len(test)},
        "class_balance": {"prevalence": float(y.mean()), "n_positive": int(y.sum()),
                          "n_total": int(len(y))},
        "caveats": [CALIBRATION_NOTE] + ([SYNTHETIC_NOTE] if cfg.synthetic else []),
        "leakage_controls": ["group-aware splits", "preprocessing inside Pipeline",
                             "threshold chosen on validation only",
                             "model selected on validation only; test evaluated once"],
    }
    if out_dir is not None:
        report["artifact_dir"] = str(save_artifact(
            best_pipe, features, cfg, report, out_dir, df=df, provenance=dataset_provenance))
    return report


# --------------------------------------------------------------------------- artifacts
def _frame_hash(df: pd.DataFrame) -> str:
    return hashlib.sha256(pd.util.hash_pandas_object(df, index=False).to_numpy().tobytes()
                          ).hexdigest()


def save_artifact(pipe: Pipeline, features: list[str], cfg: TrainConfig, report: dict,
                  out_dir: str | Path, df: pd.DataFrame | None = None,
                  provenance: dict | None = None) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, out / MODEL_FILE)
    meta = {
        "artifact_format_version": ARTIFACT_FORMAT_VERSION,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "model_name": report["selected_model"], "features": features,
        "target": cfg.target, "threshold": report["threshold"],
        "synthetic": cfg.synthetic, "calibrated": False,
        "config": {k: getattr(cfg, k) for k in cfg.__dataclass_fields__},
        "dataset_sha256_rows": _frame_hash(df[features + [cfg.target]]) if df is not None else None,
        "provenance": provenance or {},
        "test_metrics": report["test_metrics"], "caveats": report["caveats"],
        "model_sha256": hashlib.sha256((out / MODEL_FILE).read_bytes()).hexdigest(),
        "software": {"python": platform.python_version(), "sklearn": sklearn.__version__,
                     "numpy": np.__version__, "pandas": pd.__version__},
    }
    (out / META_FILE).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (out / "evaluation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return out


def load_artifact(model_dir: str | Path) -> tuple[Pipeline, dict]:
    d = Path(model_dir)
    mp, jp = d / MODEL_FILE, d / META_FILE
    if not mp.is_file() or not jp.is_file():
        raise ModelArtifactError(f"no model artifact in {d} (expected {MODEL_FILE} and {META_FILE}).")
    try:
        meta = json.loads(jp.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ModelArtifactError(f"corrupt metadata: {exc}") from exc
    if meta.get("artifact_format_version") != ARTIFACT_FORMAT_VERSION:
        raise ModelArtifactError("incompatible artifact format version "
                                 f"{meta.get('artifact_format_version')!r}.")
    if hashlib.sha256(mp.read_bytes()).hexdigest() != meta.get("model_sha256"):
        raise ModelArtifactError("model file checksum does not match metadata (corrupt/modified).")
    if meta["software"]["sklearn"].split(".")[0] != sklearn.__version__.split(".")[0]:
        raise ModelArtifactError(f"trained with scikit-learn {meta['software']['sklearn']}, "
                                 f"running {sklearn.__version__}; retrain.")
    return joblib.load(mp), meta


def predict(model_dir: str | Path, records: list[dict]) -> dict[str, Any]:
    """Validate records against the persisted feature schema, then score."""
    pipe, meta = load_artifact(model_dir)
    if not records:
        raise FeatureValidationError("no records supplied.")
    features = meta["features"]
    df = pd.DataFrame(records)
    missing = [f for f in features if f not in df.columns]
    extra = [c for c in df.columns if c not in features]
    if missing:
        raise FeatureValidationError(f"missing features: {missing}")
    if extra:
        raise FeatureValidationError(f"unexpected features: {extra}")
    df = df[features]
    try:
        df = df.apply(pd.to_numeric, errors="raise")
    except (ValueError, TypeError) as exc:
        raise FeatureValidationError(f"non-numeric feature value: {exc}") from exc
    if np.isinf(df.to_numpy(float)).any():
        raise FeatureValidationError("infinite feature values.")
    scores = _positive_score(pipe, df)
    thr = meta["threshold"]
    return {
        "model_name": meta["model_name"], "model_sha256": meta["model_sha256"],
        "created_utc": meta["created_utc"], "synthetic_training_data": meta["synthetic"],
        "calibrated": meta["calibrated"], "threshold": thr,
        "predictions": [{"score": float(s), "predicted_class": int(s >= thr)} for s in scores],
        "caveats": meta["caveats"],
    }
