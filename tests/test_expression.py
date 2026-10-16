import gzip
import hashlib

from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app

client = TestClient(app)
URL = "/v1/expression-matrices/validate"
HEADERS = {"Content-Type": "application/octet-stream"}
GOOD = b"gene\ts1\ts2\ng1\t1.5\t0\ng2\t2\t3.25\n"


def post(body: bytes):
    return client.post(URL, content=body, headers=HEADERS)


def codes(response):
    return {issue["code"] for issue in response.json()["issues"]}


def test_valid_matrix_with_checksum_and_stats():
    r = post(GOOD)
    body = r.json()
    assert r.status_code == 200
    assert body["valid"] is True
    assert (body["n_genes"], body["n_samples"]) == (2, 2)
    assert body["sample_ids"] == ["s1", "s2"]
    assert body["sha256"] == hashlib.sha256(GOOD).hexdigest()
    assert body["stats"]["max"] == 3.25
    assert body["was_gzip"] is False


def test_gzip_matrix():
    r = post(gzip.compress(GOOD))
    assert r.status_code == 200
    assert r.json()["valid"] is True
    assert r.json()["was_gzip"] is True
    assert r.json()["decompressed_bytes"] == len(GOOD)


def test_duplicate_gene_and_sample_ids():
    r = post(b"gene\ts1\ts1\ng1\t1\t2\ng1\t3\t4\n")
    assert r.status_code == 200
    assert {"duplicate_gene_ids", "duplicate_sample_ids"} <= codes(r)


def test_bad_values_are_reported():
    r = post(b"gene\ts1\ts2\ng1\t-1\tinf\ng2\tabc\t\n")
    assert r.status_code == 200
    assert r.json()["valid"] is False
    assert {"negative_values", "non_finite_values", "non_numeric_values", "missing_values"} <= codes(r)


def test_missing_ids():
    r = post(b"gene\ts1\t\n\t1\t2\n")
    assert {"missing_gene_ids", "missing_sample_ids"} <= codes(r)


def test_empty_body_is_400():
    assert post(b"").status_code == 400


def test_header_only_is_400():
    assert post(b"gene\ts1\ts2\n").status_code == 400


def test_corrupt_gzip_is_400():
    assert post(b"\x1f\x8bnot-really-gzip").status_code == 400


def test_oversize_upload_is_413(monkeypatch):
    monkeypatch.setattr(main_module, "MAX_UPLOAD_BYTES", 10)
    assert post(GOOD).status_code == 413
