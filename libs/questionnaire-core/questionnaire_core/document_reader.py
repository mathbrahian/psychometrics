from io import BytesIO

from docx import Document
from docx.table import Table
from openpyxl import load_workbook


def docx_to_text(content: bytes) -> str:
    """Extrae el texto de un .docx, con párrafos y tablas en el orden del documento."""
    document = Document(BytesIO(content))
    lines = []

    for block in document.iter_inner_content():
        if isinstance(block, Table):
            for row in block.rows:
                cells = [cell.text.strip() for cell in row.cells]
                lines.append(" | ".join(cells))
        elif block.text.strip():
            lines.append(block.text.strip())

    return "\n".join(lines)


def xlsx_sheets_to_text(content: bytes) -> list[tuple[str, str]]:
    """Extrae el texto de cada hoja de un .xlsx: lista de (nombre de la hoja, texto).

    Cada fila es una línea y sus celdas se separan con ` | `. Se omiten las filas vacías y las
    celdas vacías al final de cada fila.
    """
    workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    try:
        return [(sheet.title, _sheet_to_text(sheet)) for sheet in workbook.worksheets]
    finally:
        workbook.close()


def xlsx_to_text(content: bytes) -> str:
    """Extrae el texto de la primera hoja de un .xlsx.

    Solo se lee la primera hoja porque `/extract` devuelve un cuestionario por archivo. Para procesar
    todas las hojas está `/extract-sheets`.
    """
    sheets = xlsx_sheets_to_text(content)
    return sheets[0][1] if sheets else ""


def _sheet_to_text(sheet) -> str:
    lines = []
    for row in sheet.iter_rows(values_only=True):
        cells = ["" if value is None else str(value).strip() for value in row]
        while cells and not cells[-1]:
            cells.pop()
        if cells:
            lines.append(" | ".join(cells))
    return "\n".join(lines)
