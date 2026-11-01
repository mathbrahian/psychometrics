from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from tests.conftest import PASSWORD, USERNAME

client = TestClient(app)


def login(username=USERNAME, password=PASSWORD):
    return client.post("/auth/login", json={"usuario": username, "contrasena": password})


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def make_token(**overrides) -> str:
    now = datetime.now(UTC)
    payload = {"sub": USERNAME, "iat": now, "exp": now + timedelta(minutes=5)} | overrides
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def test_login_returns_token():
    response = login()

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600
    payload = jwt.decode(body["access_token"], settings.JWT_SECRET, algorithms=["HS256"])
    assert payload["sub"] == USERNAME


@pytest.mark.parametrize(("username", "password"), [(USERNAME, "otra"), ("otro", PASSWORD), ("otro", "otra")])
def test_login_rejects_wrong_credentials_with_same_message(username, password):
    response = login(username, password)

    assert response.status_code == 401
    assert response.json() == {"error": "credenciales_invalidas", "detalle": "Usuario o contraseña incorrectos."}
    assert response.headers["www-authenticate"] == "Bearer"


def test_login_requires_both_fields():
    response = client.post("/auth/login", json={"usuario": USERNAME})

    assert response.status_code == 422


def test_login_when_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_PASSWORD_HASH", "")

    response = login()

    assert response.status_code == 503
    assert response.json()["error"] == "servicio_no_configurado"


def test_me_with_valid_token():
    token = login().json()["access_token"]

    response = client.get("/auth/me", headers=bearer(token))

    assert response.status_code == 200
    assert response.json() == {"usuario": USERNAME}


def test_me_without_token():
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json()["error"] == "no_autenticado"


def test_me_with_expired_token():
    token = make_token(exp=datetime.now(UTC) - timedelta(minutes=1))

    response = client.get("/auth/me", headers=bearer(token))

    assert response.status_code == 401
    assert response.json()["error"] == "token_vencido"


def test_me_with_token_signed_with_other_key():
    token = jwt.encode({"sub": USERNAME, "exp": datetime.now(UTC) + timedelta(minutes=5)}, "otra-clave-cualquiera-de-32-bytes!!", algorithm="HS256")

    response = client.get("/auth/me", headers=bearer(token))

    assert response.status_code == 401
    assert response.json()["error"] == "token_invalido"


@pytest.mark.parametrize("token", ["no-es-un-jwt", "a.b.c"])
def test_me_with_malformed_token(token):
    response = client.get("/auth/me", headers=bearer(token))

    assert response.status_code == 401
    assert response.json()["error"] == "token_invalido"


def test_me_rejects_token_without_expiration():
    token = jwt.encode({"sub": USERNAME}, settings.JWT_SECRET, algorithm="HS256")

    response = client.get("/auth/me", headers=bearer(token))

    assert response.status_code == 401
    assert response.json()["error"] == "token_invalido"
