"""Capa de dominio: la entidad y el contrato del repositorio. No depende de FastAPI ni de la base de datos."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Protocol
from uuid import UUID, uuid4

from questionnaire_core.models.output_schemas import Questionnaire


class Provider(str, Enum):
    """Extractor que procesó el cuestionario."""

    VERTEX = "vertex"
    GEMINI = "gemini"


@dataclass(frozen=True)
class SavedQuestionnaire:
    """Un cuestionario extraído y guardado por el usuario."""

    questionnaire: Questionnaire
    provider: Provider
    source_filename: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def title(self) -> str | None:
        return self.questionnaire.title

    @property
    def language(self) -> str:
        return self.questionnaire.language

    @property
    def total_items(self) -> int:
        return len(self.questionnaire.items)


class QuestionnaireRepository(Protocol):
    """Contrato de persistencia. La infraestructura lo implementa (SQLAlchemy); el dominio no sabe cómo."""

    def add(self, saved: SavedQuestionnaire) -> None: ...

    def list(self) -> list[SavedQuestionnaire]: ...

    def get(self, questionnaire_id: UUID) -> SavedQuestionnaire | None: ...

    def delete(self, questionnaire_id: UUID) -> bool: ...
