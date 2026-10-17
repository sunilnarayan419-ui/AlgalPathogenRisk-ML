"""Write a Markdown model-evaluation report from a trained artifact directory."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.ml.report import write_report  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--artifact-dir", type=Path, default=Path("models/current"))
ap.add_argument("--out", type=Path, default=Path("reports/model_report.md"))
ap.add_argument("--command", default="python scripts/train_model.py --demo --out models/current")
a = ap.parse_args()
src = a.artifact_dir / "evaluation_report.json"
if not src.is_file():
    sys.exit(f"ERROR: {src} not found; train a model first.")
print(write_report(src, a.out, a.command))
