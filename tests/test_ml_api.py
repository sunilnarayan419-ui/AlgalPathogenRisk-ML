"""API tests for ML endpoints (synthetic demo data only)."""
import pytest


@pytest.fixture()
def model_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("ALGAL_MODEL_DIR", str(tmp_path / "m"))
    return tmp_path / "m"


def test_ready_reports_missing_model_without_claiming_validation(client, model_dir):
    body = client.get("/ready").json()
    assert body["model_artifact"]["loaded"] is False
    assert body["risk_model_validated"] is False


def test_predict_without_model_is_404(client, model_dir):
    r = client.post("/api/v1/models/predict", json={"records": [{"f0": 1.0}]})
    assert r.status_code == 404


def test_train_demo_then_predict(client, model_dir):
    t = client.post("/api/v1/models/train-demo", json={"seed": 1})
    assert t.status_code == 200 and any("SYNTHETIC" in c for c in t.json()["caveats"])
    meta = client.get("/api/v1/models/current").json()
    rec = {f: 0.0 for f in meta["features"]}
    r = client.post("/api/v1/models/predict", json={"records": [rec]})
    assert r.status_code == 200 and r.json()["calibrated"] is False
    bad = client.post("/api/v1/models/predict", json={"records": [{"f0": 1.0}]})
    assert bad.status_code == 422
    assert client.get("/ready").json()["model_artifact"]["loaded"] is True


def test_differential_expression_endpoint(client):
    import numpy as np
    rng = np.random.default_rng(0)
    body = {"gene_ids": [f"g{i}" for i in range(20)], "sample_ids": [f"s{i}" for i in range(8)],
            "values": rng.gamma(2, 10, (20, 8)).tolist(),
            "groups": {f"s{i}": "a" if i < 4 else "b" for i in range(8)},
            "group_a": "a", "group_b": "b", "top_n": 5}
    r = client.post("/api/v1/analysis/differential-expression", json=body)
    assert r.status_code == 200 and len(r.json()["results"]) == 5
    bad = client.post("/api/v1/analysis/differential-expression", json={**body, "group_b": "zzz"})
    assert bad.status_code == 422
    conf = {**body, "batches": {f"s{i}": "1" if i < 4 else "2" for i in range(8)}}
    assert client.post("/api/v1/analysis/differential-expression", json=conf).status_code == 409


def test_network_summary_and_uncertainty_endpoints(client):
    r = client.post("/api/v1/networks/summary", json={
        "edges": [{"a": "A", "b": "B"}, {"a": "B", "b": "C"}], "source_db": "S",
        "source_version": "1", "node": "A"})
    assert r.status_code == 200 and r.json()["neighborhood"]["nodes"] == ["A", "B"]
    assert client.post("/api/v1/networks/summary", json={
        "edges": [{"a": "A", "b": "B"}, {"a": "A", "b": "B"}], "source_db": "S",
        "source_version": "1"}).status_code == 422
    u = client.post("/api/v1/economics/uncertainty",
                    json={"p": [0, .4], "L": [100, 100], "C": [10, 10], "e": [.5, .5], "n": 5000})
    assert u.status_code == 200 and u.json()["evpi"] >= 0
    assert client.post("/api/v1/economics/uncertainty",
                       json={"p": [.5, .1], "L": [1, 1], "C": [0, 0], "e": [.5, .5]}).status_code == 422


def test_register_current_model_and_list_versions(client, model_dir):
    assert client.post("/api/v1/models/register-current").status_code == 404
    client.post("/api/v1/models/train-demo", json={"seed": 1})
    a = client.post("/api/v1/models/register-current").json()
    b = client.post("/api/v1/models/register-current").json()
    assert a["id"] == b["id"] and client.get("/api/v1/models/versions").json()[0]["synthetic"] is True
