from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.document_validation import build_input_document
from app.exceptions import ExtractionError
from app.models.output_schemas import ErrorResponse, Questionnaire
from app.questionnaire_extractor import QuestionnaireExtractor

app = FastAPI(title="extractor-vertex")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@lru_cache
def get_extractor() -> QuestionnaireExtractor:
    """Una sola instancia del extractor (y de su cliente de Vertex AI) por proceso."""
    return QuestionnaireExtractor()


@app.exception_handler(ExtractionError)
async def extraction_error_handler(_: Request, error: ExtractionError) -> JSONResponse:
    body = ErrorResponse(error=error.code, detail=str(error))
    return JSONResponse(status_code=error.status_code, content=body.model_dump())


@app.get("/")
def hello():
    return {"message": "Hola mundo desde extractor-vertex"}


@app.get("/health")
def health():
    return {"status": "ok"}


ERROR_RESPONSES = {
    status: {"model": ErrorResponse} for status in (400, 413, 415, 422, 502)
}


@app.post("/v1/questionnaires/extract", response_model=Questionnaire, responses=ERROR_RESPONSES)
async def extract_questionnaire(
    file: UploadFile,
    extractor: Annotated[QuestionnaireExtractor, Depends(get_extractor)],
) -> Questionnaire:
    """Recibe un cuestionario (PDF, .docx o .xlsx) y devuelve sus ítems estructurados."""
    content = await file.read()
    document = build_input_document(file.filename or "", content, settings.max_file_size_bytes)
    return await extractor.extract(document)
