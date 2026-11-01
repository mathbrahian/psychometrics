import hmac
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, settings
from app.exceptions import (
    AuthNotConfiguredError,
    ExpiredTokenError,
    InvalidCredentialsError,
    InvalidTokenError,
    NotAuthenticatedError,
)
from app.schemas import CurrentUser, TokenResponse

JWT_ALGORITHM = "HS256"
password_hasher = PasswordHasher()
bearer_scheme = HTTPBearer(auto_error=False)


def authenticate(username: str, password: str, config: Settings = settings) -> TokenResponse:
    """Verifica las credenciales del usuario único y devuelve un JWT firmado."""
    if not config.auth_configured:
        msg = "El inicio de sesión no está configurado en el servidor."
        raise AuthNotConfiguredError(msg)

    # Se verifica siempre la contraseña, aunque el usuario no coincida, para que el tiempo de
    # respuesta no revele si el usuario existe. El mensaje de error es el mismo en los dos casos.
    username_ok = hmac.compare_digest(username.encode(), config.AUTH_USERNAME.encode())
    try:
        password_ok = password_hasher.verify(config.AUTH_PASSWORD_HASH, password)
    except (VerificationError, InvalidHashError):
        password_ok = False

    if not (username_ok and password_ok):
        msg = "Usuario o contraseña incorrectos."
        raise InvalidCredentialsError(msg)

    expires_in = config.JWT_EXPIRE_MINUTES * 60
    now = datetime.now(UTC)
    payload = {"sub": config.AUTH_USERNAME, "iat": now, "exp": now + timedelta(seconds=expires_in)}
    token = jwt.encode(payload, config.JWT_SECRET, algorithm=JWT_ALGORITHM)
    return TokenResponse(access_token=token, expires_in=expires_in)


def decode_token(token: str, config: Settings = settings) -> CurrentUser:
    """Valida la firma y el vencimiento del JWT y devuelve el usuario."""
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[JWT_ALGORITHM], options={"require": ["exp", "sub"]})
    except jwt.ExpiredSignatureError as error:
        msg = "La sesión venció. Inicie sesión de nuevo."
        raise ExpiredTokenError(msg) from error
    except jwt.InvalidTokenError as error:
        msg = "El token no es válido."
        raise InvalidTokenError(msg) from error
    return CurrentUser(username=payload["sub"])


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> CurrentUser:
    """Dependencia para las rutas protegidas: exige `Authorization: Bearer <token>`."""
    if credentials is None:
        msg = "Falta el token de acceso."
        raise NotAuthenticatedError(msg)
    if not settings.JWT_SECRET:
        msg = "El inicio de sesión no está configurado en el servidor."
        raise AuthNotConfiguredError(msg)
    return decode_token(credentials.credentials)
