from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_hello():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Hola mundo desde extractor-vertex"}


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
