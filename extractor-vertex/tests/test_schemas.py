import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models.input_schemas import DocumentoEntrada, FormatoDocumento
from app.models.output_schemas import Cuestionario, Item, TipoItem

DATA_DIR = Path(__file__).parent / "data"


def leer_json(nombre: str) -> dict:
    return json.loads((DATA_DIR / nombre).read_text(encoding="utf-8"))


def test_ejemplo_del_enunciado_es_valido():
    cuestionario = Cuestionario.model_validate(leer_json("ejemplo_enunciado.json"))

    assert cuestionario.idioma == "it"
    assert cuestionario.total_items == 3
    assert [item.tipo for item in cuestionario.items] == [
        TipoItem.ESCALA_LIKERT,
        TipoItem.SELECCION_MULTIPLE,
        TipoItem.DESARROLLO,
    ]
    assert cuestionario.items[1].respuesta_correcta == "C"


def test_serializacion_conserva_el_esquema():
    datos = leer_json("ejemplo_enunciado.json")

    assert Cuestionario.model_validate(datos).model_dump(mode="json") == datos


def test_item_de_desarrollo_sin_alternativas_por_defecto():
    item = Item(numero=1, enunciado="Describa su día.", tipo="desarrollo")

    assert item.alternativas == []
    assert item.respuesta_correcta is None


def test_rechaza_tipo_de_item_desconocido():
    with pytest.raises(ValidationError):
        Item(numero=1, enunciado="Pregunta", tipo="abierta")


def test_rechaza_numero_de_item_menor_a_uno():
    with pytest.raises(ValidationError):
        Item(numero=0, enunciado="Pregunta", tipo="desarrollo")


@pytest.mark.parametrize("idioma", ["ita", "IT", "", "italiano"])
def test_rechaza_idioma_que_no_es_iso_639_1(idioma):
    with pytest.raises(ValidationError):
        Cuestionario(idioma=idioma, total_items=0, items=[])


def test_documento_entrada_calcula_tamano():
    documento = DocumentoEntrada(nombre_archivo="test.pdf", formato="pdf", contenido=b"12345")

    assert documento.formato == FormatoDocumento.PDF
    assert documento.tamano_bytes == 5


def test_documento_entrada_rechaza_formato_no_soportado():
    with pytest.raises(ValidationError):
        DocumentoEntrada(nombre_archivo="test.txt", formato="txt", contenido=b"hola")
