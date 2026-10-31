from enum import Enum

from pydantic import BaseModel, Field


class FormatoDocumento(str, Enum):
    """Formatos de archivo soportados."""

    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"


# Tipo MIME esperado para cada formato.
MIME_TYPES = {
    FormatoDocumento.PDF: "application/pdf",
    FormatoDocumento.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    FormatoDocumento.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class DocumentoEntrada(BaseModel):
    """Documento recibido por la API, ya leído en memoria."""

    nombre_archivo: str = Field(description="Nombre original del archivo subido.")
    formato: FormatoDocumento = Field(description="Formato del documento, según su extensión.")
    contenido: bytes = Field(description="Contenido binario del archivo.", repr=False)

    @property
    def tamano_bytes(self) -> int:
        return len(self.contenido)
