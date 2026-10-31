from enum import Enum

from pydantic import BaseModel, Field


class DocumentFormat(str, Enum):
    """Formatos de archivo soportados."""

    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"


# Tipo MIME esperado para cada formato.
MIME_TYPES = {
    DocumentFormat.PDF: "application/pdf",
    DocumentFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    DocumentFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class InputDocument(BaseModel):
    """Documento recibido por la API, ya leído en memoria."""

    filename: str = Field(description="Nombre original del archivo subido.")
    format: DocumentFormat = Field(description="Formato del documento, según su extensión.")
    content: bytes = Field(description="Contenido binario del archivo.", repr=False)

    @property
    def size_bytes(self) -> int:
        return len(self.content)
