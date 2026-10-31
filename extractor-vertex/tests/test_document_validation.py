import pytest

from app.document_validation import build_input_document, detect_format
from app.exceptions import EmptyFileError, FileTooLargeError, UnsupportedFormatError
from app.models.input_schemas import DocumentFormat

MAX_SIZE = 1024
PDF = b"%PDF-1.4 contenido"
ZIP = b"PK\x03\x04 contenido"


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("cuestionario.pdf", DocumentFormat.PDF),
        ("cuestionario.DOCX", DocumentFormat.DOCX),
        ("datos.xlsx", DocumentFormat.XLSX),
    ],
)
def test_detects_format_from_extension(filename, expected):
    assert detect_format(filename) == expected


@pytest.mark.parametrize("filename", ["cuestionario.doc", "notas.txt", "imagen.png", "sin_extension"])
def test_rejects_unsupported_extension(filename):
    with pytest.raises(UnsupportedFormatError):
        detect_format(filename)


def test_builds_input_document():
    document = build_input_document("test.pdf", PDF, MAX_SIZE)

    assert document.format == DocumentFormat.PDF
    assert document.size_bytes == len(PDF)


def test_rejects_empty_file():
    with pytest.raises(EmptyFileError):
        build_input_document("test.pdf", b"", MAX_SIZE)


def test_rejects_file_too_large():
    with pytest.raises(FileTooLargeError):
        build_input_document("test.pdf", PDF + b"x" * MAX_SIZE, MAX_SIZE)


@pytest.mark.parametrize(("filename", "content"), [("test.pdf", ZIP), ("test.docx", PDF), ("test.xlsx", b"hola")])
def test_rejects_content_that_does_not_match_extension(filename, content):
    with pytest.raises(UnsupportedFormatError):
        build_input_document(filename, content, MAX_SIZE)
