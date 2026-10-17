"""Download a STRING links file for one taxon (needs network). Default URL is UNVERIFIED:
pass --url if it fails. BioGRID requires a manual download (see docs/biological_networks.md).
"""
import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--taxon", type=int, default=3055)
    ap.add_argument("--version", default="v12.0")
    ap.add_argument("--url")
    ap.add_argument("--out", type=Path, default=Path("data/raw/interactions"))
    a = ap.parse_args()
    url = a.url or (f"https://stringdb-downloads.org/download/protein.links.detailed.{a.version}/"
                    f"{a.taxon}.protein.links.detailed.{a.version}.txt.gz")
    a.out.mkdir(parents=True, exist_ok=True)
    dest = a.out / f"string_{a.taxon}_links_detailed_{a.version}.txt.gz"
    try:
        urllib.request.urlretrieve(url, dest)  # noqa: S310
    except (urllib.error.URLError, OSError) as exc:
        print(f"ERROR downloading {url}: {exc}", file=sys.stderr)
        return 1
    print(dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
