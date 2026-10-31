import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models.input_schemas import DocumentFormat, InputDocument
from app.models.output_schemas import Item, ItemType, Questionnaire
from tests.conftest import EXAMPLES_DIR

DATA_DIR = Path(__file__).parent / "data"


def read_json(filename: str) -> dict:
    return json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))


def test_spec_example_is_valid():
    questionnaire = Questionnaire.model_validate(read_json("spec_example.json"))

    assert questionnaire.language == "it"
    assert questionnaire.total_items == 3
    assert [item.type for item in questionnaire.items] == [
        ItemType.LIKERT_SCALE,
        ItemType.MULTIPLE_CHOICE,
        ItemType.OPEN_ENDED,
    ]
    assert questionnaire.items[1].correct_answer == "C"


def test_serialization_uses_spanish_field_names():
    data = read_json("spec_example.json")

    assert Questionnaire.model_validate(data).model_dump(mode="json") == data


def test_accepts_english_field_names():
    item = Item(number=1, statement="Describa su día.", type=ItemType.OPEN_ENDED)

    assert item.model_dump(mode="json") == {
        "numero": 1,
        "enunciado": "Describa su día.",
        "tipo": "desarrollo",
        "alternativas": [],
        "respuesta_correcta": None,
    }


def test_open_ended_item_has_no_options_by_default():
    item = Item(numero=1, enunciado="Describa su día.", tipo="desarrollo")

    assert item.options == []
    assert item.correct_answer is None


def test_rejects_unknown_item_type():
    with pytest.raises(ValidationError):
        Item(numero=1, enunciado="Pregunta", tipo="abierta")


def test_rejects_item_number_below_one():
    with pytest.raises(ValidationError):
        Item(numero=0, enunciado="Pregunta", tipo="desarrollo")


@pytest.mark.parametrize("language", ["ita", "IT", "", "italiano"])
def test_rejects_language_not_iso_639_1(language):
    with pytest.raises(ValidationError):
        Questionnaire(idioma=language, total_items=0, items=[])


def test_input_document_computes_size():
    document = InputDocument(filename="test.pdf", format="pdf", content=b"12345")

    assert document.format == DocumentFormat.PDF
    assert document.size_bytes == 5


def test_input_document_rejects_unsupported_format():
    with pytest.raises(ValidationError):
        InputDocument(filename="test.txt", format="txt", content=b"hola")


@pytest.mark.parametrize("result_file", sorted(EXAMPLES_DIR.glob("*/resultado.json")), ids=lambda p: p.parent.name)
def test_example_results_match_schema(result_file):
    data = json.loads(result_file.read_text(encoding="utf-8"))

    questionnaire = Questionnaire.model_validate(data)

    assert questionnaire.total_items == len(questionnaire.items)
