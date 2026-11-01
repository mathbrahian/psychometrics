from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field
from questionnaire_core.models.output_schemas import Questionnaire

from app.questionnaires.domain import Provider, SavedQuestionnaire
from app.schemas import SPANISH_JSON


class SaveQuestionnaireRequest(BaseModel):
    """Cuestionario extraído que el usuario quiere guardar."""

    model_config = SPANISH_JSON

    provider: Provider = Field(alias="proveedor", description="Extractor que lo procesó.")
    source_filename: str = Field(alias="archivo_origen", min_length=1, max_length=255)
    questionnaire: Questionnaire = Field(alias="cuestionario")


class QuestionnaireSummary(BaseModel):
    """Datos de un cuestionario guardado, sin sus ítems. Es lo que se muestra en la lista."""

    model_config = SPANISH_JSON

    id: UUID
    title: str | None = Field(alias="titulo")
    language: str = Field(alias="idioma")
    total_items: int
    provider: Provider = Field(alias="proveedor")
    source_filename: str = Field(alias="archivo_origen")
    created_at: datetime = Field(alias="creado_en")

    @classmethod
    def from_entity(cls, saved: SavedQuestionnaire) -> "QuestionnaireSummary":
        return cls(
            id=saved.id,
            title=saved.title,
            language=saved.language,
            total_items=saved.total_items,
            provider=saved.provider,
            source_filename=saved.source_filename,
            created_at=saved.created_at,
        )


class QuestionnaireDetail(QuestionnaireSummary):
    """Cuestionario guardado completo, con sus ítems."""

    questionnaire: Questionnaire = Field(alias="cuestionario")

    @classmethod
    def from_entity(cls, saved: SavedQuestionnaire) -> "QuestionnaireDetail":
        summary = QuestionnaireSummary.from_entity(saved)
        return cls(**summary.model_dump(by_alias=False), questionnaire=saved.questionnaire)
