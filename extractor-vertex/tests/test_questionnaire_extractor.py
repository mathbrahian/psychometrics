import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from google.genai import types

from app.exceptions import (
    InvalidModelResponseError,
    NoItemsFoundError,
    TruncatedResponseError,
    UnsupportedFormatError,
)
from app.models.input_schemas import InputDocument
from app.models.output_schemas import Questionnaire
from app.questionnaire_extractor import QuestionnaireExtractor
from tests.conftest import EXAMPLES_DIR

SPEC_EXAMPLE = (Path(__file__).parent / "data" / "spec_example.json").read_text(encoding="utf-8")
PDF_DOCUMENT = InputDocument(filename="test.pdf", format="pdf", content=b"%PDF-1.4 fake")


class FakeModels:
    """Simula client.aio.models: guarda la llamada y devuelve una respuesta fija."""

    def __init__(self, text: str | None, finish_reason=types.FinishReason.STOP):
        self.response = SimpleNamespace(text=text, candidates=[SimpleNamespace(finish_reason=finish_reason)])
        self.calls = []

    async def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def make_extractor(text: str | None, finish_reason=types.FinishReason.STOP):
    models = FakeModels(text, finish_reason)
    client = SimpleNamespace(aio=SimpleNamespace(models=models))
    return QuestionnaireExtractor(client=client), models


async def test_extracts_questionnaire_from_model_response():
    extractor, _ = make_extractor(SPEC_EXAMPLE)

    questionnaire = await extractor.extract(PDF_DOCUMENT)

    assert questionnaire == Questionnaire.model_validate_json(SPEC_EXAMPLE)


async def test_makes_a_single_call_with_the_pdf():
    extractor, models = make_extractor(SPEC_EXAMPLE)

    await extractor.extract(PDF_DOCUMENT)

    assert len(models.calls) == 1
    [part] = models.calls[0]["contents"]
    assert part.inline_data.mime_type == "application/pdf"
    assert part.inline_data.data == PDF_DOCUMENT.content


def test_config_requests_json_with_questionnaire_schema():
    extractor, _ = make_extractor(SPEC_EXAMPLE)

    assert extractor.config.response_mime_type == "application/json"
    assert extractor.config.response_json_schema == Questionnaire.model_json_schema()
    assert all(s.threshold == types.HarmBlockThreshold.OFF for s in extractor.config.safety_settings)


async def test_raises_when_response_is_truncated():
    extractor, _ = make_extractor('{"titulo": "Cuest', types.FinishReason.MAX_TOKENS)

    with pytest.raises(TruncatedResponseError):
        await extractor.extract(PDF_DOCUMENT)


async def test_raises_when_response_is_empty():
    extractor, _ = make_extractor(None, types.FinishReason.SAFETY)

    with pytest.raises(InvalidModelResponseError):
        await extractor.extract(PDF_DOCUMENT)


async def test_raises_when_response_does_not_match_schema():
    extractor, _ = make_extractor(json.dumps({"titulo": "X", "items": []}))

    with pytest.raises(InvalidModelResponseError):
        await extractor.extract(PDF_DOCUMENT)


async def test_raises_when_no_items_found():
    extractor, _ = make_extractor(json.dumps({"titulo": None, "idioma": "es", "total_items": 0, "items": []}))

    with pytest.raises(NoItemsFoundError):
        await extractor.extract(PDF_DOCUMENT)


async def test_sends_docx_as_text():
    extractor, models = make_extractor(SPEC_EXAMPLE)
    content = (EXAMPLES_DIR / "01-tipo-doc" / "cuestionario.docx").read_bytes()
    document = InputDocument(filename="cuestionario.docx", format="docx", content=content)

    await extractor.extract(document)

    [part] = models.calls[0]["contents"]
    assert part.text.startswith("Cuestionario de ejemplo")


async def test_xlsx_not_supported_yet():
    extractor, models = make_extractor(SPEC_EXAMPLE)
    document = InputDocument(filename="test.xlsx", format="xlsx", content=b"PK\x03\x04")

    with pytest.raises(UnsupportedFormatError):
        await extractor.extract(document)
    assert models.calls == []
