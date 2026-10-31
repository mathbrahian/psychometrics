from enum import Enum

from pydantic import BaseModel, Field


class TipoItem(str, Enum):
    """Tipos de ítem que se pueden identificar en un cuestionario."""

    ESCALA_LIKERT = "escala_likert"
    SELECCION_MULTIPLE = "seleccion_multiple"
    VERDADERO_FALSO = "verdadero_falso"
    DESARROLLO = "desarrollo"
    EMPAREJAMIENTO = "emparejamiento"


class Alternativa(BaseModel):
    """Una alternativa de respuesta de un ítem."""

    valor: int | str = Field(
        description="Valor de la alternativa: un número en escalas Likert (0, 1, 2...) "
        "o una letra en selección múltiple (A, B, C...).",
        examples=[0, "A"],
    )
    texto: str = Field(description="Texto de la alternativa, tal como aparece en el documento.")


class Item(BaseModel):
    """Un ítem (pregunta o afirmación) del cuestionario."""

    numero: int = Field(ge=1, description="Número del ítem dentro del cuestionario, empezando en 1.")
    enunciado: str = Field(description="Texto de la pregunta o afirmación.")
    tipo: TipoItem = Field(description="Tipo de ítem.")
    alternativas: list[Alternativa] = Field(
        default_factory=list,
        description="Alternativas de respuesta. Vacía en ítems de desarrollo.",
    )
    respuesta_correcta: int | str | None = Field(
        default=None,
        description="Valor de la alternativa correcta, solo si el documento la indica.",
    )


class Cuestionario(BaseModel):
    """Resultado de la extracción: el cuestionario estructurado."""

    titulo: str | None = Field(default=None, description="Título del cuestionario, si el documento lo tiene.")
    idioma: str = Field(
        pattern=r"^[a-z]{2}$",
        description="Idioma del documento en código ISO 639-1 (por ejemplo: it, es, en).",
        examples=["it", "es", "en"],
    )
    total_items: int = Field(ge=0, description="Cantidad de ítems extraídos.")
    items: list[Item] = Field(description="Ítems del cuestionario, en el orden del documento.")


class ErrorRespuesta(BaseModel):
    """Respuesta de la API cuando ocurre un error."""

    error: str = Field(description="Código del error.", examples=["formato_invalido", "sin_items"])
    detalle: str = Field(description="Descripción del error para el usuario.")
