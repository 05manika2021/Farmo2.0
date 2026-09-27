import os

os.environ["DATABASE_URL"] = "sqlite:///./test_farmo.db"
os.environ["DEMO_MODE"] = "true"
os.environ["GEMINI_API_KEY"] = ""
os.environ["TWOFACTOR_API_KEY"] = ""
os.environ["MAPTILER_API_KEY"] = ""
os.environ["GOOGLE_MAPS_API_KEY"] = ""
os.environ["GROQ_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["WEATHER_API_KEY"] = ""
os.environ["WEATHER_PROVIDER"] = "disabled"
os.environ["STT_PROVIDER"] = "groq"
os.environ["TTS_PROVIDER"] = "gemini"

import pytest
from app.db.database import engine, Base
from app.db.seed import init_db, seed_demo_data


@pytest.fixture(autouse=True, scope="session")
def setup_database():
    init_db()
    seed_demo_data()
    yield
    Base.metadata.drop_all(bind=engine)
    try:
        os.remove("test_farmo.db")
    except OSError:
        pass


@pytest.fixture(scope="session")
def client():
    from app.main import app
    from starlette.testclient import TestClient
    with TestClient(app) as c:
        yield c
