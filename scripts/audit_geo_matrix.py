import argparse
import json
from pathlib import Path
from app.services.metadata import audit_geo_series_matrix

def main():
    parser = argparse.ArgumentParser(description="Audit a GEO series-matrix metadata file.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = audit_geo_series_matrix(args.input)
    payload = json.dumps(result, indent=2)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload + "\n", encoding="utf-8")
    print(payload)

if __name__ == "__main__":
    main()
