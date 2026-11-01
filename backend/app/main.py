from typing import Annotated

from fastapi import Depends, FastAPI, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from questionnaire_core.models.output_schemas import ErrorResponse, Questionnaire, SheetResult

from app.auth import authenticate, get_current_user
from app.config import settings
from app.exceptions import BackendError
from app.extractors import ExtractorClient, Provider, get_extractor_client
from app.schemas import CurrentUser, LoginRequest, TokenResponse

app = FastAPI(title="backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


@app.exception_handler(BackendError)
async def backend_error_handler(_: Request, error: BackendError) -> JSONResponse:
    body = ErrorResponse(error=error.code, detail=str(error))
    headers = {"WWW-Authenticate": "Bearer"} if error.status_code == 401 else None
    return JSONResponse(status_code=error.status_code, content=body.model_dump(), headers=headers)


AUTH_ERRORS = {status: {"model": ErrorResponse} for status in (401, 503)}


@app.get("/")
def hello():
    return {"message": "Hola mundo desde backend"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/login", response_model=TokenResponse, responses=AUTH_ERRORS)
def login(credentials: LoginRequest) -> TokenResponse:
    """Inicia sesión con el usuario único y devuelve un token de acceso (JWT)."""
    return authenticate(credentials.username, credentials.password)


@app.get("/auth/me", response_model=CurrentUser, responses=AUTH_ERRORS)
def me(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    """Devuelve el usuario autenticado. Es la primera ruta protegida."""
    return user


EXTRACTION_ERRORS = {status: {"model": ErrorResponse} for status in (400, 401, 413, 415, 422, 429, 502, 503, 504)}


async def forward_to_extractor(
    path: str, file: UploadFile, provider: Provider, client: ExtractorClient
) -> JSONResponse:
    content = await file.read()
    status, body = await client.forward(provider, path, file.filename or "", content, file.content_type)
    return JSONResponse(status_code=status, content=body)


@app.post(
    "/v1/questionnaires/extract",
    response_model=Questionnaire,
    responses=EXTRACTION_ERRORS,
    dependencies=[Depends(get_current_user)],
)
async def extract_questionnaire(
    file: UploadFile,
    client: Annotated[ExtractorClient, Depends(get_extractor_client)],
    proveedor: Provider = Provider.GEMINI,
):
    """Extrae los ítems de un cuestionario (PDF, .docx o .xlsx) con el extractor elegido.

    Requiere sesión iniciada. La respuesta del extractor, incluidos sus errores, se devuelve sin cambios.
    """
    return await forward_to_extractor("/v1/questionnaires/extract", file, proveedor, client)


@app.post(
    "/v1/questionnaires/extract-sheets",
    response_model=list[SheetResult],
    responses=EXTRACTION_ERRORS,
    dependencies=[Depends(get_current_user)],
)
async def extract_questionnaire_sheets(
    file: UploadFile,
    client: Annotated[ExtractorClient, Depends(get_extractor_client)],
    proveedor: Provider = Provider.GEMINI,
):
    """Procesa cada hoja de un Excel (.xlsx) como un cuestionario, con el extractor elegido.

    Requiere sesión iniciada.
    """
    return await forward_to_extractor("/v1/questionnaires/extract-sheets", file, proveedor, client)
