"""Shared fixtures. Requires fastapi/sqlalchemy (installed via `pip install -e .[dev]`)."""
import pytest


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    from sqlalchemy.pool import StaticPool

    from app.database.connection import get_db, init_db, make_engine
    from app.main import app

    engine = make_engine("sqlite://", connect_args={"check_same_thread": False},
                         poolclass=StaticPool)
    init_db(engine)

    def override():
        from sqlalchemy.orm import sessionmaker as sm
        s = sm(bind=engine, expire_on_commit=False)()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()
