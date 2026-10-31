from questionnaire_core.document_reader import docx_to_text, xlsx_to_text
from tests.conftest import EXAMPLES_DIR


def test_extracts_text_from_docx_in_order():
    content = (EXAMPLES_DIR / "01-tipo-doc" / "cuestionario.docx").read_bytes()

    text = docx_to_text(content)

    assert text.startswith("Cuestionario de ejemplo")
    assert text.index("Pregunta 1") < text.index("Pregunta 2") < text.index("Pregunta 3")
    assert "C. 32" in text


def test_extracts_only_first_sheet_from_xlsx():
    content = (EXAMPLES_DIR / "02-tipo-xlsx" / "cuestionario.xlsx").read_bytes()

    text = xlsx_to_text(content)
    lines = text.splitlines()

    assert lines[0] == "Cuestionario de ejemplo – Bienestar y razonamiento"
    assert lines[2].startswith("N° | Enunciado | Tipo")
    assert lines[-1].startswith("10 | Relacione cada país con su capital.")
    # Las demás hojas (otros idiomas, resultado esperado y guía) no se incluyen.
    assert "Questionario" not in text
    assert "escala_likert" not in text
    assert "Guía" not in text


def test_xlsx_rows_drop_trailing_empty_cells():
    content = (EXAMPLES_DIR / "02-tipo-xlsx" / "cuestionario.xlsx").read_bytes()

    lines = xlsx_to_text(content).splitlines()

    assert lines[3] == "1 | Me preocupo en exceso por cosas de poca importancia. | Escala Likert | Nunca | A veces | Frecuentemente | Siempre"
