from io import BytesIO

from docx import Document
from docx.table import Table


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
