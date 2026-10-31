from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from questionnaire_core.exceptions import ServiceNotConfiguredError

from app import main
from app.main import app


def test_hello():
    response = TestClient(app).get("/")

    assert response.json() == {"message": "Hola mundo desde extractor-gemini"}


def test_builds_gemini_api_client(monkeypatch):
    calls = []
    monkeypatch.setattr(main.genai, "Client", lambda **kwargs: calls.append(kwargs) or object())
    monkeypatch.setattr(main.settings, "GEMINI_API_KEY", "clave-de-prueba")

    extractor = main.build_extractor()

    assert calls == [{"api_key": "clave-de-prueba"}]
    assert extractor.settings is main.settings


def test_requires_api_key(monkeypatch):
    monkeypatch.setattr(main.settings, "GEMINI_API_KEY", "")

    with pytest.raises(ServiceNotConfiguredError):
        main.build_extractor()


def test_endpoint_reports_missing_api_key(monkeypatch):
    monkeypatch.setattr(main.settings, "GEMINI_API_KEY", "")
    app.state.extractor = None
    docx = Path(__file__).resolve().parents[2] / "examples" / "01-tipo-doc" / "cuestionario.docx"

    with open(docx, "rb") as file:
        response = TestClient(app).post("/v1/questionnaires/extract", files={"file": ("cuestionario.docx", file)})

    assert response.status_code == 503
    assert response.json()["error"] == "servicio_no_configurado"
