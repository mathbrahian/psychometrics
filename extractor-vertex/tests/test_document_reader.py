from app.document_reader import docx_to_text
from tests.conftest import EXAMPLES_DIR


def test_extracts_text_from_docx_in_order():
    content = (EXAMPLES_DIR / "01-tipo-doc" / "cuestionario.docx").read_bytes()

    text = docx_to_text(content)

    assert text.startswith("Cuestionario de ejemplo")
    assert text.index("Pregunta 1") < text.index("Pregunta 2") < text.index("Pregunta 3")
    assert "C. 32" in text
