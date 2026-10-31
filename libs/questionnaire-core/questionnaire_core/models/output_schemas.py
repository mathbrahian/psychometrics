from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

# Los campos se nombran en inglés en el código, pero el JSON usa los nombres en español
# que exige la prueba (alias). Se aceptan ambos al validar y se serializa con los alias.
SPANISH_JSON = ConfigDict(validate_by_name=True, validate_by_alias=True, serialize_by_alias=True)


class ItemType(str, Enum):
    """Tipos de ítem que se pueden identificar en un cuestionario."""

    LIKERT_SCALE = "escala_likert"
    MULTIPLE_CHOICE = "seleccion_multiple"
    TRUE_FALSE = "verdadero_falso"
    OPEN_ENDED = "desarrollo"
    MATCHING = "emparejamiento"


class Option(BaseModel):
    """Una alternativa de respuesta de un ítem."""

    model_config = SPANISH_JSON

    value: int | str = Field(
        alias="valor",
        description="Valor de la alternativa: un número en escalas Likert (0, 1, 2...) "
        "o una letra en selección múltiple (A, B, C...).",
        examples=[0, "A"],
    )
    text: str = Field(alias="texto", description="Texto de la alternativa, tal como aparece en el documento.")


class Item(BaseModel):
    """Un ítem (pregunta o afirmación) del cuestionario."""

    model_config = SPANISH_JSON

    number: int = Field(alias="numero", ge=1, description="Número del ítem dentro del cuestionario, empezando en 1.")
    statement: str = Field(alias="enunciado", description="Texto de la pregunta o afirmación.")
    type: ItemType = Field(alias="tipo", description="Tipo de ítem.")
    options: list[Option] = Field(
        alias="alternativas",
        default_factory=list,
        description="Alternativas de respuesta. Vacía en ítems de desarrollo.",
    )
    correct_answer: int | str | None = Field(
        alias="respuesta_correcta",
        default=None,
        description="Valor de la alternativa correcta, solo si el documento la indica.",
    )


class Questionnaire(BaseModel):
    """Resultado de la extracción: el cuestionario estructurado."""

    model_config = SPANISH_JSON

    title: str | None = Field(alias="titulo", default=None, description="Título del cuestionario, si el documento lo tiene.")
    language: str = Field(
        alias="idioma",
        pattern=r"^[a-z]{2}$",
        description="Idioma del documento en código ISO 639-1 (por ejemplo: it, es, en).",
        examples=["it", "es", "en"],
    )
    total_items: int = Field(ge=0, description="Cantidad de ítems extraídos.")
    items: list[Item] = Field(description="Ítems del cuestionario, en el orden del documento.")


class ErrorResponse(BaseModel):
    """Respuesta de la API cuando ocurre un error."""

    model_config = SPANISH_JSON

    error: str = Field(description="Código del error.", examples=["formato_invalido", "sin_items"])
    detail: str = Field(alias="detalle", description="Descripción del error para el usuario.")


class SheetResult(BaseModel):
    """Resultado de una hoja de un Excel: el cuestionario extraído o el error de esa hoja."""

    model_config = SPANISH_JSON

    sheet_name: str = Field(alias="hoja", description="Nombre de la hoja del Excel.")
    questionnaire: Questionnaire | None = Field(
        alias="cuestionario", default=None, description="Cuestionario extraído, si la hoja se procesó bien."
    )
    error: ErrorResponse | None = Field(default=None, description="Error de la hoja, si no se pudo procesar.")
