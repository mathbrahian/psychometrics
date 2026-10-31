from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, FastAPI, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from questionnaire_core.document_validation import build_input_document
from questionnaire_core.exceptions import ExtractionError, UnsupportedFormatError
from questionnaire_core.extractor import QuestionnaireExtractor
from questionnaire_core.models.input_schemas import DocumentFormat
from questionnaire_core.models.output_schemas import ErrorResponse, Questionnaire, SheetResult
from questionnaire_core.settings import ExtractorSettings

ERROR_RESPONSES = {status: {"model": ErrorResponse} for status in (400, 413, 415, 422, 429, 502)}


def get_extractor(request: Request) -> QuestionnaireExtractor:
    """Crea el extractor la primera vez que se usa: una sola instancia (y un solo cliente) por proceso.

    Se crea al primer request y no al arrancar, para que el servicio y sus tests no necesiten
    credenciales hasta que de verdad se llama al modelo.
    """
    state = request.app.state
    if state.extractor is None:
        state.extractor = state.extractor_factory()
    return state.extractor


def create_app(
    title: str,
    settings: ExtractorSettings,
    extractor_factory: Callable[[], QuestionnaireExtractor],
) -> FastAPI:
    """Crea la API de extracción. Los servicios solo cambian el `extractor_factory` (el proveedor)."""
    app = FastAPI(title=title)
    app.state.extractor_factory = extractor_factory
    app.state.extractor = None

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.exception_handler(ExtractionError)
    async def extraction_error_handler(_: Request, error: ExtractionError) -> JSONResponse:
        body = ErrorResponse(error=error.code, detail=str(error))
        return JSONResponse(status_code=error.status_code, content=body.model_dump())

    @app.get("/")
    def hello():
        return {"message": f"Hola mundo desde {title}"}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/v1/questionnaires/extract", response_model=Questionnaire, responses=ERROR_RESPONSES)
    async def extract_questionnaire(
        file: UploadFile,
        extractor: Annotated[QuestionnaireExtractor, Depends(get_extractor)],
    ) -> Questionnaire:
        """Recibe un cuestionario (PDF, .docx o .xlsx) y devuelve sus ítems estructurados."""
        content = await file.read()
        document = build_input_document(file.filename or "", content, settings.max_file_size_bytes)
        return await extractor.extract(document)

    @app.post("/v1/questionnaires/extract-sheets", response_model=list[SheetResult], responses=ERROR_RESPONSES)
    async def extract_questionnaire_sheets(
        file: UploadFile,
        extractor: Annotated[QuestionnaireExtractor, Depends(get_extractor)],
    ) -> list[SheetResult]:
        """Recibe un Excel (.xlsx) y procesa cada hoja como un cuestionario independiente, en paralelo.

        Devuelve un resultado por hoja con contenido: el cuestionario o el error de esa hoja.
        """
        content = await file.read()
        document = build_input_document(file.filename or "", content, settings.max_file_size_bytes)
        if document.format != DocumentFormat.XLSX:
            msg = "Este endpoint solo acepta archivos .xlsx."
            raise UnsupportedFormatError(msg)
        return await extractor.extract_sheets(document)

    return app
