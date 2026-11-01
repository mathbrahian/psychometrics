"""Capa de infraestructura: implementación del repositorio con SQLAlchemy y PostgreSQL."""

from datetime import datetime
from uuid import UUID

from questionnaire_core.models.output_schemas import Questionnaire
from sqlalchemy import JSON, DateTime, Integer, String, Uuid, delete, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.db import Base
from app.questionnaires.domain import Provider, SavedQuestionnaire


class QuestionnaireRow(Base):
    """Tabla `questionnaires`: columnas para listar y filtrar, y el cuestionario completo en JSONB."""

    __tablename__ = "questionnaires"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    title: Mapped[str | None] = mapped_column(String(500))
    language: Mapped[str] = mapped_column(String(2))
    total_items: Mapped[int] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(String(20))
    source_filename: Mapped[str] = mapped_column(String(255))
    # JSONB en PostgreSQL; JSON genérico en otros motores (por ejemplo, SQLite en los tests).
    content: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


def to_row(saved: SavedQuestionnaire) -> QuestionnaireRow:
    return QuestionnaireRow(
        id=saved.id,
        title=saved.title,
        language=saved.language,
        total_items=saved.total_items,
        provider=saved.provider.value,
        source_filename=saved.source_filename,
        content=saved.questionnaire.model_dump(mode="json"),
        created_at=saved.created_at,
    )


def to_entity(row: QuestionnaireRow) -> SavedQuestionnaire:
    return SavedQuestionnaire(
        id=row.id,
        questionnaire=Questionnaire.model_validate(row.content),
        provider=Provider(row.provider),
        source_filename=row.source_filename,
        created_at=row.created_at,
    )


class SqlQuestionnaireRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, saved: SavedQuestionnaire) -> None:
        self.session.add(to_row(saved))
        self.session.commit()

    def list(self) -> list[SavedQuestionnaire]:
        rows = self.session.scalars(select(QuestionnaireRow).order_by(QuestionnaireRow.created_at.desc()))
        return [to_entity(row) for row in rows]

    def get(self, questionnaire_id: UUID) -> SavedQuestionnaire | None:
        row = self.session.get(QuestionnaireRow, questionnaire_id)
        return to_entity(row) if row else None

    def delete(self, questionnaire_id: UUID) -> bool:
        result = self.session.execute(delete(QuestionnaireRow).where(QuestionnaireRow.id == questionnaire_id))
        self.session.commit()
        return result.rowcount > 0
