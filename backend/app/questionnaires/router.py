"""Capa de API: endpoints de los cuestionarios guardados. Todos requieren sesión iniciada."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from questionnaire_core.models.output_schemas import ErrorResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_session
from app.questionnaires.schemas import QuestionnaireDetail, QuestionnaireSummary, SaveQuestionnaireRequest
from app.questionnaires.service import QuestionnaireService
from app.questionnaires.sql_repository import SqlQuestionnaireRepository

router = APIRouter(prefix="/v1/questionnaires", tags=["cuestionarios guardados"], dependencies=[Depends(get_current_user)])

ERRORS = {code: {"model": ErrorResponse} for code in (401, 404, 503)}


def get_service(session: Annotated[Session, Depends(get_session)]) -> QuestionnaireService:
    return QuestionnaireService(SqlQuestionnaireRepository(session))


Service = Annotated[QuestionnaireService, Depends(get_service)]


@router.post("", response_model=QuestionnaireDetail, status_code=status.HTTP_201_CREATED, responses=ERRORS)
def save_questionnaire(request: SaveQuestionnaireRequest, service: Service) -> QuestionnaireDetail:
    """Guarda un cuestionario extraído."""
    saved = service.save(request.questionnaire, request.provider, request.source_filename)
    return QuestionnaireDetail.from_entity(saved)


@router.get("", response_model=list[QuestionnaireSummary], responses=ERRORS)
def list_questionnaires(service: Service) -> list[QuestionnaireSummary]:
    """Lista los cuestionarios guardados, del más reciente al más antiguo, sin sus ítems."""
    return [QuestionnaireSummary.from_entity(saved) for saved in service.list()]


@router.get("/{questionnaire_id}", response_model=QuestionnaireDetail, responses=ERRORS)
def get_questionnaire(questionnaire_id: UUID, service: Service) -> QuestionnaireDetail:
    """Devuelve un cuestionario guardado completo."""
    return QuestionnaireDetail.from_entity(service.get(questionnaire_id))


@router.delete("/{questionnaire_id}", status_code=status.HTTP_204_NO_CONTENT, responses=ERRORS)
def delete_questionnaire(questionnaire_id: UUID, service: Service) -> Response:
    """Elimina un cuestionario guardado."""
    service.delete(questionnaire_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
