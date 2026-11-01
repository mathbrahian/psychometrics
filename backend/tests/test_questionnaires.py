import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.main import app
from app.questionnaires import sql_repository  # noqa: F401  registra la tabla en Base.metadata
from tests.conftest import PASSWORD, USERNAME

EXAMPLE = json.loads((Path(__file__).resolve().parents[2] / "examples" / "01-tipo-doc" / "resultado.json").read_text())
client = TestClient(app)


@pytest.fixture(autouse=True)
def database():
    """Base SQLite en memoria por test. En producción es PostgreSQL; el modelo usa JSON genérico fuera de PostgreSQL."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    make_session = sessionmaker(bind=engine, expire_on_commit=False)

    def override():
        session = make_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def auth():
    token = client.post("/auth/login", json={"usuario": USERNAME, "contrasena": PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def save(auth, provider="gemini", filename="cuestionario.docx"):
    body = {"proveedor": provider, "archivo_origen": filename, "cuestionario": EXAMPLE}
    return client.post("/v1/questionnaires", json=body, headers=auth)


def test_save_returns_detail_with_spanish_field_names(auth):
    response = save(auth)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "titulo", "idioma", "total_items", "proveedor", "archivo_origen", "creado_en", "cuestionario"}
    assert body["titulo"] == EXAMPLE["titulo"]
    assert body["total_items"] == len(EXAMPLE["items"])
    assert body["cuestionario"] == EXAMPLE


def test_list_returns_summaries_newest_first(auth):
    first = save(auth, filename="primero.docx").json()
    second = save(auth, provider="vertex", filename="segundo.pdf").json()

    response = client.get("/v1/questionnaires", headers=auth)

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [second["id"], first["id"]]
    assert "cuestionario" not in response.json()[0]
    assert response.json()[0]["proveedor"] == "vertex"


def test_get_returns_full_questionnaire(auth):
    saved = save(auth).json()

    response = client.get(f"/v1/questionnaires/{saved['id']}", headers=auth)

    assert response.status_code == 200
    assert response.json()["cuestionario"] == EXAMPLE


def test_delete_removes_questionnaire(auth):
    saved = save(auth).json()

    response = client.delete(f"/v1/questionnaires/{saved['id']}", headers=auth)

    assert response.status_code == 204
    assert client.get(f"/v1/questionnaires/{saved['id']}", headers=auth).status_code == 404
    assert client.get("/v1/questionnaires", headers=auth).json() == []


@pytest.mark.parametrize("method", ["get", "delete"])
def test_unknown_id_returns_404(auth, method):
    response = getattr(client, method)(f"/v1/questionnaires/{uuid4()}", headers=auth)

    assert response.status_code == 404
    assert response.json()["error"] == "cuestionario_no_encontrado"


def test_invalid_id_returns_422(auth):
    assert client.get("/v1/questionnaires/no-es-un-uuid", headers=auth).status_code == 422


def test_save_rejects_invalid_questionnaire(auth):
    body = {"proveedor": "gemini", "archivo_origen": "x.docx", "cuestionario": {"titulo": "sin items"}}

    assert client.post("/v1/questionnaires", json=body, headers=auth).status_code == 422


def test_save_rejects_unknown_provider(auth):
    body = {"proveedor": "otro", "archivo_origen": "x.docx", "cuestionario": EXAMPLE}

    assert client.post("/v1/questionnaires", json=body, headers=auth).status_code == 422


@pytest.mark.parametrize(
    ("method", "path"),
    [("get", "/v1/questionnaires"), ("post", "/v1/questionnaires"), ("get", f"/v1/questionnaires/{uuid4()}"), ("delete", f"/v1/questionnaires/{uuid4()}")],
)
def test_all_endpoints_require_login(method, path):
    response = getattr(client, method)(path)

    assert response.status_code == 401
