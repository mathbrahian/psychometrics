import pytest
from argon2 import PasswordHasher

from app.config import settings

USERNAME = "evaluador"
PASSWORD = "contraseña-de-prueba"


@pytest.fixture(autouse=True)
def auth_settings(monkeypatch):
    """Usuario de prueba: los tests nunca usan las credenciales reales."""
    monkeypatch.setattr(settings, "AUTH_USERNAME", USERNAME)
    monkeypatch.setattr(settings, "AUTH_PASSWORD_HASH", PasswordHasher().hash(PASSWORD))
    monkeypatch.setattr(settings, "JWT_SECRET", "clave-de-prueba-para-firmar-tokens-1234567890")
    monkeypatch.setattr(settings, "JWT_EXPIRE_MINUTES", 60)
