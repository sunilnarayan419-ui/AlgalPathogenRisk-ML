"""NOT EXECUTED in the authoring sandbox (fastapi unavailable). Run `pytest` locally."""
GOOD = b"gene\ts1\ts2\ng1\t1.5\t0\ng2\t2\t3.25\n"  # synthetic


def test_models_status_reports_unavailable(client):
    r = client.get("/api/v1/models/status")
    assert r.status_code == 200 and r.json()["risk_model"]["available"] is False


def test_networks_status(client):
    assert client.get("/api/v1/networks/status").json()["external_interaction_databases_configured"] == []


def test_power_continuous_and_unsupported(client):
    r = client.post("/api/v1/experiments/power-analysis", json={"endpoint": "continuous", "effect_size_d": 0.5})
    assert r.status_code == 200 and r.json()["n_group1"] == 64
    assert client.post("/api/v1/experiments/power-analysis", json={"endpoint": "time_to_event"}).status_code == 422
    assert client.post("/api/v1/experiments/power-analysis", json={"endpoint": "continuous"}).status_code == 422


def test_design_requires_complete_spec_and_persists(client):
    assert client.post("/api/v1/experiments/design", json={}).status_code == 422
    spec = dict(objective="o", hypothesis="h", primary_endpoint="e", experimental_unit="flask",
                biological_replicate_definition="independent flask", groups=["c", "t"],
                control_group="c", primary_analysis="Welch", sample_size_rationale="assumed",
                randomization_method="seeded", biosafety_statement="approval required",
                save_as="exp1")
    assert client.post("/api/v1/experiments/design", json=spec).status_code == 200
    assert client.post("/api/v1/experiments/design", json=spec).status_code == 409


def test_randomize_and_duplicate_units(client):
    ok = client.post("/api/v1/experiments/randomize", json={"unit_ids": ["a", "b", "c", "d"], "groups": ["x", "y"], "seed": 1})
    assert ok.status_code == 200 and len(ok.json()["assignments"]) == 4
    bad = client.post("/api/v1/experiments/randomize", json={"unit_ids": ["a", "a"], "groups": ["x", "y"], "seed": 1})
    assert bad.status_code == 422


def test_analyze(client):
    r = client.post("/api/v1/experiments/analyze", json={"values": [1, 2, 3, 4, 5, 6], "groups": list("aaabbb"), "group_a": "a", "group_b": "b"})
    assert r.status_code == 200 and "ci" in r.json()


def test_economics_endpoints(client):
    r = client.post("/api/v1/economics/break-even", json={"p": 0.4, "L": 1000, "C": 100, "e": 0.5, "cycles": 3})
    assert r.json()["net_benefit_total"] == 300
    assert client.post("/api/v1/economics/break-even", json={"p": 1.5, "L": 1, "C": 1, "e": 0.5}).status_code == 422
    s = client.post("/api/v1/economics/sensitivity", json={"L": 1000, "C": 100, "p_values": [0.1, 0.5], "e_values": [0.5]})
    assert len(s.json()["grid"]) == 2


def test_models_evaluate_refuses_ungrouped_and_small(client):
    m = [[float(i % 3), float(i)] for i in range(8)]
    labels = list("AAAABBBB")
    assert client.post("/api/v1/models/evaluate", json={"matrix": m, "labels": labels}).status_code == 422


def test_dataset_audit_registers_and_is_idempotent(client):
    a = client.post("/api/v1/datasets/audit", content=GOOD, headers={"Content-Type": "application/octet-stream"})
    assert a.status_code == 200 and a.json()["valid"] is True
    b = client.post("/api/v1/datasets/audit", content=GOOD, headers={"Content-Type": "application/octet-stream"})
    assert b.json()["dataset_version_id"] == a.json()["dataset_version_id"]
    lst = client.get("/api/v1/datasets").json()
    assert lst[0]["accession"] == "GSE128981" and lst[0]["n_versions"] == 1
    assert client.get("/api/v1/datasets/9999").status_code == 404
    assert client.post("/api/v1/datasets/audit", content=b"").status_code == 400


def test_networks_status_lists_loaders(client):
    body = client.get("/api/v1/networks/status").json()
    assert body["external_interaction_databases_configured"] == []
    assert any("STRING" in s for s in body["supported_loaders"])
