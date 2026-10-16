from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["risk_model_loaded"] is False
    assert response.json()["biological_validation"] == "not_established"

def test_economics_endpoint():
    response = client.post("/v1/economics/break-even", json={
        "intervention_cost": 100, "collapse_loss": 1000,
        "intervention_effectiveness": 0.5, "baseline_collapse_probability": 0.4,
        "pilot_batches": 3})
    assert response.status_code == 200
    assert response.json()["pilot_expected_net_value"] == 300


def test_audit_returns_404_when_matrix_missing(monkeypatch, tmp_path):
    import app.main as main_module
    monkeypatch.setattr(main_module, "DEFAULT_MATRIX", tmp_path / "missing.txt")
    response = client.get("/v1/datasets/GSE128981/audit")
    assert response.status_code == 404
