"""NOT EXECUTED in the authoring sandbox (sqlalchemy unavailable)."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.database import models as m
from app.database import repositories as repo
from app.database.connection import init_db, make_engine, session_scope


def test_schema_constraints_and_provenance():
    engine = make_engine("sqlite://")
    init_db(engine)
    with session_scope(engine) as s:
        ds = repo.get_or_create_dataset(s, "GSE_TEST")
        v1 = repo.register_version(s, ds, "f.tsv", "a" * 64, 10)
        assert repo.register_version(s, ds, "f.tsv", "a" * 64, 10).id == v1.id
        repo.save_run(s, "exploratory", {"k": 1}, 42, {"python": "x"}, v1.id)
    with pytest.raises(IntegrityError):
        with session_scope(engine) as s:
            s.add(m.DatasetVersion(dataset_id=999, file_name="x", sha256="b" * 64, size_bytes=1))
