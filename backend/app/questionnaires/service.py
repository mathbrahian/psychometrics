"""Capa de aplicación: los casos de uso. Orquestan el dominio a través del repositorio."""

from uuid import UUID

from questionnaire_core.models.output_schemas import Questionnaire

from app.exceptions import QuestionnaireNotFoundError
from app.questionnaires.domain import Provider, QuestionnaireRepository, SavedQuestionnaire


class QuestionnaireService:
    def __init__(self, repository: QuestionnaireRepository):
        self.repository = repository

    def save(self, questionnaire: Questionnaire, provider: Provider, source_filename: str) -> SavedQuestionnaire:
        saved = SavedQuestionnaire(questionnaire=questionnaire, provider=provider, source_filename=source_filename)
        self.repository.add(saved)
        return saved

    def list(self) -> list[SavedQuestionnaire]:
        return self.repository.list()

    def get(self, questionnaire_id: UUID) -> SavedQuestionnaire:
        saved = self.repository.get(questionnaire_id)
        if saved is None:
            raise QuestionnaireNotFoundError(f"No existe el cuestionario {questionnaire_id}.")
        return saved

    def delete(self, questionnaire_id: UUID) -> None:
        if not self.repository.delete(questionnaire_id):
            raise QuestionnaireNotFoundError(f"No existe el cuestionario {questionnaire_id}.")
