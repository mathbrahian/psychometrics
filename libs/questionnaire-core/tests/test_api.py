import pytest
from fastapi.testclient import TestClient

from questionnaire_core.api import get_extractor
from questionnaire_core.exceptions import InvalidModelResponseError, NoItemsFoundError, RateLimitError
from questionnaire_core.models.output_schemas import Questionnaire
from tests.conftest import DATA_DIR, EXAMPLES_DIR
from tests.conftest import test_app as app

URL = "/v1/questionnaires/extract"
SPEC_EXAMPLE = Questionnaire.model_validate_json((DATA_DIR / "spec_example.json").read_text(encoding="utf-8"))
DOCX = (EXAMPLES_DIR / "01-tipo-doc" / "cuestionario.docx").read_bytes()


class FakeExtractor:
    def __init__(self, result=SPEC_EXAMPLE, error=None):
        self.result = result
        self.error = error
        self.documents = []

    async def extract(self, document):
        self.documents.append(document)
        if self.error:
            raise self.error
        return self.result


@pytest.fixture
def fake_extractor():
    extractor = FakeExtractor()
    app.dependency_overrides[get_extractor] = lambda: extractor
    yield extractor
    app.dependency_overrides.clear()


client = TestClient(app)


def upload(filename: str, content: bytes):
    return client.post(URL, files={"file": (filename, content)})


def test_returns_questionnaire_with_spanish_field_names(fake_extractor):
    response = upload("cuestionario.docx", DOCX)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"titulo", "idioma", "total_items", "items"}
    assert body["items"][0]["enunciado"] == SPEC_EXAMPLE.items[0].statement


def test_passes_validated_document_to_extractor(fake_extractor):
    upload("cuestionario.docx", DOCX)

    [document] = fake_extractor.documents
    assert document.filename == "cuestionario.docx"
    assert document.content == DOCX


@pytest.mark.parametrize(
    ("filename", "content", "status", "code"),
    [
        ("cuestionario.doc", b"\xd0\xcf\x11\xe0", 415, "formato_invalido"),
        ("cuestionario.pdf", DOCX, 415, "formato_invalido"),
        ("cuestionario.pdf", b"", 400, "archivo_vacio"),
    ],
)
def test_returns_error_for_invalid_files(fake_extractor, filename, content, status, code):
    response = upload(filename, content)

    assert response.status_code == status
    assert response.json()["error"] == code
    assert "detalle" in response.json()
    assert fake_extractor.documents == []


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (NoItemsFoundError("No se detectaron ítems."), 422, "sin_items"),
        (InvalidModelResponseError("Respuesta inválida."), 502, "respuesta_invalida"),
        (RateLimitError("Límite de uso."), 429, "limite_de_uso"),
    ],
)
def test_returns_error_from_extractor(fake_extractor, error, status, code):
    fake_extractor.error = error

    response = upload("cuestionario.docx", DOCX)

    assert response.status_code == status
    assert response.json() == {"error": code, "detalle": str(error)}


def test_requires_file(fake_extractor):
    response = client.post(URL)

    assert response.status_code == 422
    assert fake_extractor.documents == []


def test_accepts_xlsx(fake_extractor):
    content = (EXAMPLES_DIR / "02-tipo-xlsx" / "cuestionario.xlsx").read_bytes()

    response = upload("cuestionario.xlsx", content)

    assert response.status_code == 200
    assert fake_extractor.documents[0].format.value == "xlsx"


def test_accepts_pdf(fake_extractor):
    content = (EXAMPLES_DIR / "03-tipo-pdf" / "cuestionario.pdf").read_bytes()

    response = upload("cuestionario.pdf", content)

    assert response.status_code == 200
    assert fake_extractor.documents[0].format.value == "pdf"


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_configured_origin():
    response = client.get("/", headers={"Origin": "http://localhost:3000"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_rejects_other_origin():
    response = client.get("/", headers={"Origin": "http://otro-sitio.com"})

    assert "access-control-allow-origin" not in response.headers
