import httpx
import pytest
from fastapi.testclient import TestClient

from app import extractors
from app.config import settings
from app.extractors import ExtractorClient, get_extractor_client
from app.main import app
from tests.conftest import PASSWORD, USERNAME

client = TestClient(app)
QUESTIONNAIRE = {"titulo": "Test", "idioma": "es", "total_items": 0, "items": []}


class FakeExtractors:
    """Simula los extractores: guarda las peticiones y responde lo indicado."""

    def __init__(self, status=200, body=QUESTIONNAIRE, error=None):
        self.status, self.body, self.error = status, body, error
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.error:
            raise self.error
        return httpx.Response(self.status, json=self.body)


@pytest.fixture
def extractors_mock(monkeypatch):
    monkeypatch.setattr(settings, "EXTRACTOR_VERTEX_URL", "http://extractor-vertex:8080")
    monkeypatch.setattr(settings, "EXTRACTOR_GEMINI_URL", "http://extractor-gemini:7070")
    monkeypatch.setattr(settings, "EXTRACTOR_AUTH", "none")
    fake = FakeExtractors()
    app.dependency_overrides[get_extractor_client] = lambda: ExtractorClient(transport=httpx.MockTransport(fake.handler))
    yield fake
    app.dependency_overrides.clear()


@pytest.fixture
def token():
    return client.post("/auth/login", json={"usuario": USERNAME, "contrasena": PASSWORD}).json()["access_token"]


def extract(token=None, path="/v1/questionnaires/extract", params=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    files = {"file": ("cuestionario.docx", b"PK\x03\x04 contenido", "application/octet-stream")}
    return client.post(path, files=files, headers=headers, params=params)


def test_requires_login(extractors_mock):
    response = extract()

    assert response.status_code == 401
    assert response.json()["error"] == "no_autenticado"
    assert extractors_mock.requests == []


def test_uses_gemini_by_default(extractors_mock, token):
    response = extract(token)

    assert response.status_code == 200
    assert response.json() == QUESTIONNAIRE
    [request] = extractors_mock.requests
    assert str(request.url) == "http://extractor-gemini:7070/v1/questionnaires/extract"


@pytest.mark.parametrize(
    ("provider", "path", "expected_url"),
    [
        ("vertex", "/v1/questionnaires/extract", "http://extractor-vertex:8080/v1/questionnaires/extract"),
        ("gemini", "/v1/questionnaires/extract-sheets", "http://extractor-gemini:7070/v1/questionnaires/extract-sheets"),
        ("vertex", "/v1/questionnaires/extract-sheets", "http://extractor-vertex:8080/v1/questionnaires/extract-sheets"),
    ],
)
def test_forwards_to_chosen_extractor(extractors_mock, token, provider, path, expected_url):
    extract(token, path=path, params={"proveedor": provider})

    [request] = extractors_mock.requests
    assert str(request.url) == expected_url


def test_forwards_the_file(extractors_mock, token):
    extract(token)

    [request] = extractors_mock.requests
    body = request.read()
    assert b'filename="cuestionario.docx"' in body
    assert b"PK\x03\x04 contenido" in body


def test_rejects_unknown_provider(extractors_mock, token):
    response = extract(token, params={"proveedor": "otro"})

    assert response.status_code == 422
    assert extractors_mock.requests == []


def test_returns_extractor_errors_unchanged(extractors_mock, token):
    extractors_mock.status = 415
    extractors_mock.body = {"error": "formato_invalido", "detalle": "El formato '.doc' no está soportado."}

    response = extract(token)

    assert response.status_code == 415
    assert response.json() == extractors_mock.body


def test_timeout_returns_504(extractors_mock, token):
    extractors_mock.error = httpx.ReadTimeout("lento")

    response = extract(token)

    assert response.status_code == 504
    assert response.json()["error"] == "tiempo_agotado"


def test_connection_error_returns_502(extractors_mock, token):
    extractors_mock.error = httpx.ConnectError("caído")

    response = extract(token)

    assert response.status_code == 502
    assert response.json()["error"] == "extractor_no_disponible"


def test_non_json_response_returns_502(extractors_mock, token):
    app.dependency_overrides[get_extractor_client] = lambda: ExtractorClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(403, text="<html>Forbidden</html>"))
    )

    response = extract(token)

    assert response.status_code == 502
    assert "HTTP 403" in response.json()["detalle"]


def test_extractor_not_configured_returns_503(extractors_mock, token, monkeypatch):
    monkeypatch.setattr(settings, "EXTRACTOR_GEMINI_URL", "")

    response = extract(token)

    assert response.status_code == 503
    assert extractors_mock.requests == []


def test_sends_google_id_token_in_cloud_run(extractors_mock, token, monkeypatch):
    monkeypatch.setattr(settings, "EXTRACTOR_AUTH", "id_token")
    audiences = []
    monkeypatch.setattr(extractors, "fetch_id_token", lambda audience: audiences.append(audience) or "token-de-google")

    extract(token)

    [request] = extractors_mock.requests
    assert request.headers["authorization"] == "Bearer token-de-google"
    assert audiences == ["http://extractor-gemini:7070"]


def test_no_id_token_in_local(extractors_mock, token):
    extract(token)

    [request] = extractors_mock.requests
    assert "authorization" not in request.headers
