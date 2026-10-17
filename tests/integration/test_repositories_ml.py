"""DB repository tests for runs, model versions and networks (need sqlalchemy)."""
import pytest
from sqlalchemy.orm import sessionmaker

from app.database import repositories as repo
from app.database.connection import init_db, make_engine
from app.ml import pipeline as mlp


@pytest.fixture()
def db():
    engine = make_engine("sqlite://")
    init_db(engine)
    s = sessionmaker(bind=engine, expire_on_commit=False)()
    yield s
    s.close()


def test_model_version_registration_is_idempotent(db, tmp_path):
    mlp.train_and_evaluate(mlp.make_demo_dataset(), mlp.TrainConfig(synthetic=True), out_dir=tmp_path)
    _, meta = mlp.load_artifact(tmp_path)
    a = repo.register_model_version(db, meta, str(tmp_path))
    b = repo.register_model_version(db, meta, str(tmp_path))
    assert a.id == b.id and a.synthetic is True and a.calibrated is False
    assert len(repo.list_model_versions(db)) == 1


def test_runs_and_evaluations_roundtrip(db):
    run = repo.create_analysis_run(db, "ml_training", {"seed": 1}, seed=1)
    ev = repo.save_model_evaluation(db, run, "label", {"auc": 0.7}, "synthetic", exploratory=True)
    assert repo.get_analysis_run(db, run.id).kind == "ml_training" and ev.analysis_run_id == run.id
    assert repo.get_analysis_run(db, 999) is None
    with pytest.raises(ValueError):
        repo.create_analysis_run(db, "", {})


def test_network_registration_rejects_duplicates(db):
    repo.register_network(db, "net", {"STRING": "v12"}, 10, 20)
    with pytest.raises(ValueError, match="already"):
        repo.register_network(db, "net", {}, 1, 1)
    assert repo.get_network(db, "net").n_edges == 20 and repo.get_network(db, "zzz") is None
