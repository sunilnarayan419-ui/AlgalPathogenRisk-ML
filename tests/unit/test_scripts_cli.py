"""Run the CLIs as users would (subprocess), on SYNTHETIC / metadata-only fixtures."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures"


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True,
                          cwd=ROOT)


def test_manifest_and_audit_on_real_metadata(tmp_path):
    r = run("scripts/audit_geo_matrix.py", "--input", FIX / "GSE128981_series_matrix.txt",
            "--manifest-dir", tmp_path, "--gse128981-batch-rule")
    assert r.returncode == 0, r.stderr
    import pandas as pd
    man = pd.read_csv(tmp_path / "sample_manifest.csv")
    assert len(man) == 21 and set(man["batch"]) == {"batch1", "batch2"}
    a = run("scripts/audit_dataset.py", "--series-matrix", FIX / "GSE128981_series_matrix.txt",
            "--out", tmp_path / "audit")
    assert a.returncode == 0, a.stderr
    rep = json.loads((tmp_path / "audit" / "audit.json").read_text())
    assert rep["qc"] is None and rep["suitability"]["supports"] == []


def test_analysis_runs_and_refuses_confounded_contrast(tmp_path):
    run("scripts/audit_geo_matrix.py", "--input", FIX / "GSE128981_series_matrix.txt",
        "--manifest-dir", tmp_path, "--gse128981-batch-rule")
    base = ["scripts/run_analysis.py", "--fpkm", FIX / "SYNTHETIC_fpkm_gse128981_layout.tsv",
            "--metadata", tmp_path / "sample_metadata_gsm.csv", "--batch-col", "batch"]
    ok = run(*base, "--out", tmp_path / "o1", "--contrast", "UVM4", "Elow47")
    assert ok.returncode == 0, ok.stderr
    assert (tmp_path / "o1" / "de_log2fpkm_UVM4_vs_Elow47.csv").is_file()
    bad = run(*base, "--out", tmp_path / "o2", "--contrast", "UVM11-C1", "Elow47")
    assert bad.returncode == 3 and "REFUSED" in bad.stderr


def test_train_cli_demo_and_missing_file_errors(tmp_path):
    r = run("scripts/train_model.py", "--demo", "--out", tmp_path / "m")
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "m" / "model.joblib").is_file()
    assert run("scripts/make_model_report.py", "--artifact-dir", tmp_path / "none").returncode != 0
