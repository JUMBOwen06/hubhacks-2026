import os
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

# Build the test database in a temp folder, never in the repo.
_TMP = Path(tempfile.mkdtemp(prefix="hubhacks-test-"))
os.environ["HUBHACKS_DB"] = str(_TMP / "test.db")
os.environ["HUBHACKS_REBUILD_ON_START"] = "1"


@pytest.fixture(scope="session")
def built_db():
    from app import build
    return build.build_database()


@pytest.fixture()
def conn(built_db):
    from app import config, db
    c = db.connect(config.db_path())
    yield c
    c.close()


@pytest.fixture(scope="session")
def client(built_db):
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c
