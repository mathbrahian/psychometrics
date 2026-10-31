from pathlib import Path

from app.exceptions import EmptyFileError, FileTooLargeError, UnsupportedFormatError
from app.models.input_schemas import DocumentFormat, InputDocument

# Firma de los primeros bytes de cada formato. .docx y .xlsx son archivos ZIP.
PDF_SIGNATURE = b"%PDF"
ZIP_SIGNATURE = b"PK\x03\x04"


def detect_format(filename: str) -> DocumentFormat:
    """Obtiene el formato a partir de la extensión del archivo."""
    extension = Path(filename).suffix.lower().lstrip(".")
    try:
        return DocumentFormat(extension)
    except ValueError:
        supported = ", ".join(f".{f.value}" for f in DocumentFormat)
        msg = f"El formato '.{extension}' no está soportado. Formatos válidos: {supported}."
        raise UnsupportedFormatError(msg) from None


def content_matches_format(content: bytes, document_format: DocumentFormat) -> bool:
    """Verifica que el contenido real del archivo corresponda a su extensión."""
    if document_format == DocumentFormat.PDF:
        return content.startswith(PDF_SIGNATURE)
    return content.startswith(ZIP_SIGNATURE)


def build_input_document(filename: str, content: bytes, max_size_bytes: int) -> InputDocument:
    """Valida el archivo subido y lo convierte en un InputDocument."""
    document_format = detect_format(filename)

    if not content:
        msg = "El archivo está vacío."
        raise EmptyFileError(msg)

    if len(content) > max_size_bytes:
        msg = f"El archivo supera el tamaño máximo de {max_size_bytes // (1024 * 1024)} MB."
        raise FileTooLargeError(msg)

    if not content_matches_format(content, document_format):
        msg = f"El contenido del archivo no corresponde a un .{document_format.value} válido."
        raise UnsupportedFormatError(msg)

    return InputDocument(filename=filename, format=document_format, content=content)
