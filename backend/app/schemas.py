from pydantic import BaseModel, ConfigDict, Field

SPANISH_JSON = ConfigDict(validate_by_name=True, validate_by_alias=True, serialize_by_alias=True)


class LoginRequest(BaseModel):
    """Credenciales del usuario."""

    model_config = SPANISH_JSON

    username: str = Field(alias="usuario", min_length=1)
    password: str = Field(alias="contrasena", min_length=1)


class TokenResponse(BaseModel):
    """Token de acceso. Los nombres siguen el estándar OAuth 2.0 (RFC 6749), por eso están en inglés."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Segundos hasta que vence el token.")


class CurrentUser(BaseModel):
    """Usuario autenticado."""

    model_config = SPANISH_JSON

    username: str = Field(alias="usuario")
