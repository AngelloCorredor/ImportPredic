import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("APP_SECRET_KEY", "clave-solo-para-pruebas")
os.environ.pop("OPENROUTER_API_KEY", None)


@pytest.fixture
def db(tmp_path):
    from src.db.engine import reset_engine

    reset_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    from src.db import repository

    return repository
