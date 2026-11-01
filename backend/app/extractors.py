import asyncio
import logging
from enum import Enum

import google.auth.transport.requests
import google.oauth2.id_token
import httpx

from app.config import Settings, settings
from app.exceptions import ExtractorNotConfiguredError, ExtractorTimeoutError, ExtractorUnavailableError

logger = logging.getLogger("backend")


class Provider(str, Enum):
    """Extractor que procesa el cuestionario."""

    VERTEX = "vertex"
    GEMINI = "gemini"


def fetch_id_token(audience: str) -> str:
    """Pide a Google un token de identidad de la service account del servicio, para la URL del extractor."""
    return google.oauth2.id_token.fetch_id_token(google.auth.transport.requests.Request(), audience)


class ExtractorClient:
    """Reenvía archivos a los extractores y devuelve su respuesta tal cual (código HTTP y JSON)."""

    def __init__(self, config: Settings = settings, transport: httpx.AsyncBaseTransport | None = None):
        self.config = config
        self.transport = transport

    def base_url(self, provider: Provider) -> str:
        url = {Provider.VERTEX: self.config.EXTRACTOR_VERTEX_URL, Provider.GEMINI: self.config.EXTRACTOR_GEMINI_URL}[provider]
        if not url:
            msg = f"El extractor '{provider.value}' no está configurado en el servidor."
            raise ExtractorNotConfiguredError(msg)
        return url.rstrip("/")

    async def auth_headers(self, base_url: str) -> dict[str, str]:
        if self.config.EXTRACTOR_AUTH != "id_token":
            return {}
        token = await asyncio.to_thread(fetch_id_token, base_url)
        return {"Authorization": f"Bearer {token}"}

    async def forward(
        self, provider: Provider, path: str, filename: str, content: bytes, content_type: str | None
    ) -> tuple[int, object]:
        base_url = self.base_url(provider)
        headers = await self.auth_headers(base_url)
        files = {"file": (filename, content, content_type or "application/octet-stream")}

        try:
            async with httpx.AsyncClient(transport=self.transport, timeout=self.config.EXTRACTOR_TIMEOUT_SECONDS) as client:
                response = await client.post(f"{base_url}{path}", files=files, headers=headers)
        except httpx.TimeoutException as error:
            msg = f"El extractor '{provider.value}' tardó demasiado en responder."
            raise ExtractorTimeoutError(msg) from error
        except httpx.HTTPError as error:
            logger.error("No se pudo conectar con el extractor %s: %s", provider.value, error)
            msg = f"No se pudo conectar con el extractor '{provider.value}'."
            raise ExtractorUnavailableError(msg) from error

        try:
            body = response.json()
        except ValueError:
            # Por ejemplo, un 403 de Cloud Run en HTML si el backend no tiene permiso para invocar el extractor.
            logger.error("Respuesta no JSON del extractor %s: HTTP %s", provider.value, response.status_code)
            msg = f"El extractor '{provider.value}' respondió con un error (HTTP {response.status_code})."
            raise ExtractorUnavailableError(msg) from None
        return response.status_code, body


def get_extractor_client() -> ExtractorClient:
    return ExtractorClient()
