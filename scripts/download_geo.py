"""Download GSE128981 files from NCBI GEO and record SHA-256 checksums (needs network).

    python scripts/download_geo.py --out data/raw
The URLs are the ones listed in the series-matrix header (FPKM) and the standard GEO series-matrix
path. Check GEO's terms of use before redistributing files. Not executed by the authors offline.
"""
import argparse
import gzip
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

FILES = {
    "GSE128981_series_matrix.txt.gz":
        "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE128nnn/GSE128981/matrix/GSE128981_series_matrix.txt.gz",
    "GSE128981_FPKMs.replicates.v2.tsv.gz":
        "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE128nnn/GSE128981/suppl/GSE128981_FPKMs.replicates.v2.tsv.gz",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path("data/raw"))
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, url in FILES.items():
        dest = a.out / name
        if dest.exists() and not a.force:
            print(f"exists, skipping: {dest}")
        else:
            try:
                urllib.request.urlretrieve(url, dest)  # noqa: S310 (fixed https URLs above)
            except (urllib.error.URLError, OSError) as exc:
                print(f"ERROR downloading {url}: {exc}", file=sys.stderr)
                return 1
        try:
            with gzip.open(dest, "rb") as fh:
                while fh.read(1 << 20):
                    pass
        except (OSError, EOFError) as exc:
            print(f"ERROR: {dest} is not a valid gzip file: {exc}", file=sys.stderr)
            return 1
        manifest[name] = {"url": url, "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
                          "bytes": dest.stat().st_size}
    (a.out / "download_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
