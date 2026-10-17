"""Exploratory, leakage-safe classification baseline + honest model-availability status.

This evaluates a GENOTYPE/strain-group label only. It never produces infection or
culture-collapse probabilities.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, confusion_matrix
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

RISK_MODEL_STATUS = {
    "available": False,
    "reason": ("No outcome-labelled data (infection, stress-induced collapse, production "
               "failure) exists in GSE128981; genotype labels are not risk labels."),
    "required_for_availability": ["defined prediction target and horizon",
                                  "independent biological units with measured outcomes",
                                  "group/batch-aware validation", "external validation"],
}

CAVEAT = ("Exploratory within-dataset estimate on very few biological samples. Not external "
          "validation; does not show a biologically useful predictor.")


def _pipelines(seed: int) -> dict[str, Pipeline]:
    return {
        "dummy_most_frequent": Pipeline([("clf", DummyClassifier(strategy="most_frequent"))]),
        "logistic_l2": Pipeline([("scale", StandardScaler()),
                                 ("clf", LogisticRegression(C=0.1, max_iter=5000,
                                                            random_state=seed))]),
    }


def evaluate_group_baseline(X: pd.DataFrame, y, groups=None, seed: int = 42,
                            min_per_class: int = 3, n_splits: int = 3,
                            allow_ungrouped: bool = False) -> dict:
    """Cross-validated baselines. Scaling happens inside each training fold.

    X: samples x features. groups: independent-unit/batch id per sample; samples sharing a
    group are never split across train/test. Without groups, ungrouped CV is refused unless
    allow_ungrouped=True (then replicate leakage must be ruled out by the caller).
    """
    y = np.asarray(y)
    if len(y) != len(X):
        raise ValueError("X and y length mismatch.")
    if not np.isfinite(X.to_numpy(dtype=float)).all():
        raise ValueError("X contains NaN/inf.")
    classes, counts = np.unique(y, return_counts=True)
    if len(classes) < 2:
        raise ValueError("Target needs at least 2 classes.")
    if groups is None and not allow_ungrouped:
        raise ValueError("groups required to prevent replicate leakage "
                         "(or pass allow_ungrouped=True explicitly).")
    unavailable = {"status": "insufficient_data", "metrics": None, "caveat": CAVEAT}
    if counts.min() < min_per_class:
        return {**unavailable, "reason": f"smallest class has {counts.min()} samples "
                                          f"(< {min_per_class}); no performance estimate."}
    if groups is not None:
        groups = np.asarray(groups)
        n_groups_per_class = min(len(set(groups[y == c])) for c in classes)
        if n_groups_per_class < n_splits:
            return {**unavailable, "reason": f"only {n_groups_per_class} independent groups in "
                                             f"the rarest class (< {n_splits} folds)."}
        cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        split_kwargs = {"groups": groups}
    else:
        cv = StratifiedKFold(n_splits=min(n_splits, counts.min()), shuffle=True,
                             random_state=seed)
        split_kwargs = {}
    results = {}
    for name, pipe in _pipelines(seed).items():
        pred = cross_val_predict(pipe, X.to_numpy(float), y, cv=cv, **split_kwargs)
        results[name] = {"balanced_accuracy": float(balanced_accuracy_score(y, pred)),
                         "confusion_matrix": confusion_matrix(y, pred, labels=classes).tolist()}
    return {"status": "evaluated_exploratory", "classes": classes.tolist(), "metrics": results,
            "cv": type(cv).__name__, "n_splits": n_splits, "seed": seed,
            "grouped": groups is not None, "caveat": CAVEAT}
