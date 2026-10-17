"""Render evaluation_report.json (+ metadata.json) into a reproducible Markdown report."""
from __future__ import annotations

import json
from pathlib import Path


def _fmt(v) -> str:
    return "n/a" if v is None else (f"{v:.3f}" if isinstance(v, float) else str(v))


def render_markdown(report: dict, repro_command: str) -> str:
    ds, tm, dm = report["dataset"], report["test_metrics"], report["dummy_baseline_test_metrics"]
    cm = tm["confusion_matrix"]
    L = ["# Model evaluation report", ""]
    if ds["synthetic"]:
        L += ["> **SYNTHETIC DATA.** Results show that the software runs. They are not biological "
              "evidence and say nothing about real pathogen risk.", ""]
    L += ["## Dataset", f"- Rows: {ds['n_rows']}; independent groups: {ds['n_groups']}; "
          f"features: {ds['n_features']}",
          f"- Target: `{ds['target']}` (binary 0/1); prevalence "
          f"{report['class_balance']['prevalence']:.3f} "
          f"({report['class_balance']['n_positive']}/{report['class_balance']['n_total']})",
          f"- Group column (leakage control): `{ds['group_column']}`",
          f"- Provenance: `{json.dumps(ds['provenance'], sort_keys=True)}`",
          f"- Features: {', '.join(f'`{f}`' for f in ds['features'])}", "",
          "## Methodology",
          f"- Splits (rows): {report['split_sizes']}; groups never cross splits.",
          f"- Model selected on validation `{report['selection_metric']}`; threshold "
          f"`{report['threshold']:.4f}` by {report['threshold_criterion']}; test set scored once.",
          "- Leakage controls: " + "; ".join(report["leakage_controls"]), "",
          "## Candidate models (validation)",
          "| Model | CV AP (mean ± sd) | Val AP | Val ROC-AUC | Val F1 |", "|---|---|---|---|---|"]
    for name, r in report["candidates"].items():
        v = r["validation"]
        L.append(f"| {name}{' **(selected)**' if name == report['selected_model'] else ''} | "
                 f"{_fmt(r['cv_average_precision_mean'])} ± {_fmt(r['cv_average_precision_sd'])} | "
                 f"{_fmt(v['average_precision'])} | {_fmt(v['roc_auc'])} | {_fmt(v['f1'])} |")
    L += ["", "## Held-out test results", "| Metric | Selected | Dummy baseline |", "|---|---|---|"]
    for k in ("roc_auc", "average_precision", "precision", "recall_sensitivity", "specificity",
              "f1", "brier"):
        L.append(f"| {k} | {_fmt(tm[k])} | {_fmt(dm[k])} |")
    L += ["", f"Confusion matrix (test, n={tm['n']}): TN={cm['tn']} FP={cm['fp']} "
          f"FN={cm['fn']} TP={cm['tp']}", "", "## Error analysis"]
    e = report["test_errors"]
    L += [f"- False positives: {e['n_false_positive_rows']} rows "
          f"(units: {', '.join(e['false_positive_units']) or 'none'})",
          f"- False negatives: {e['n_false_negative_rows']} rows "
          f"(units: {', '.join(e['false_negative_units']) or 'none'})",
          "- Calibration (test, quantile bins; noisy at small n):"]
    for b in report["test_calibration_table"]:
        L.append(f"  - mean score {b['mean_score']:.2f} → observed rate {b['observed_rate']:.2f} (n={b['n']})")
    L += ["", "## Limitations and leakage risks"] + [f"- {c}" for c in report["caveats"]]
    L += ["- Small test sets give wide, unquantified uncertainty on every metric above.",
          "- No external validation; no calibration step was applied.",
          "- Group ids must reflect true independence (culture, batch, lineage); wrong ids leak.",
          "", "## Reproduce", f"```\n{repro_command}\n```", ""]
    return "\n".join(L)


def write_report(eval_json: str | Path, out_md: str | Path,
                 repro_command: str = "python scripts/train_model.py --demo --out models/current") -> Path:
    report = json.loads(Path(eval_json).read_text(encoding="utf-8"))
    out = Path(out_md)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_markdown(report, repro_command), encoding="utf-8")
    return out
