from fastapi.testclient import TestClient

from app import main
from app.main import app


def test_hello():
    response = TestClient(app).get("/")

    assert response.json() == {"message": "Hola mundo desde extractor-vertex"}


def test_builds_vertex_client(monkeypatch):
    calls = []
    monkeypatch.setattr(main.genai, "Client", lambda **kwargs: calls.append(kwargs) or object())
    monkeypatch.setattr(main.settings, "GOOGLE_CLOUD_PROJECT", "mi-proyecto")

    extractor = main.build_extractor()

    assert calls == [{"vertexai": True, "project": "mi-proyecto", "location": "global"}]
    assert extractor.settings is main.settings
