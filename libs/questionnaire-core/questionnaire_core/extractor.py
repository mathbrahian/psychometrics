import asyncio
import logging

from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from questionnaire_core.document_reader import docx_to_text, xlsx_sheets_to_text, xlsx_to_text
from questionnaire_core.exceptions import (
    ExtractionError,
    InvalidModelResponseError,
    ModelServiceError,
    NoItemsFoundError,
    RateLimitError,
    TooManySheetsError,
    TruncatedResponseError,
    UnsupportedFormatError,
)
from questionnaire_core.models.input_schemas import MIME_TYPES, DocumentFormat, InputDocument
from questionnaire_core.models.output_schemas import ErrorResponse, Questionnaire, SheetResult
from questionnaire_core.settings import ExtractorSettings

logger = logging.getLogger("questionnaire-core")

SYSTEM_INSTRUCTION = """
Eres un sistema que digitaliza cuestionarios y pruebas de evaluación psicométrica.
Recibes un documento y devuelves TODOS sus ítems en el JSON del esquema indicado.

Reglas generales:
- Extrae los ítems en el mismo orden en que aparecen en el documento.
- `numero` es consecutivo, empezando en 1, aunque el documento use otra numeración.
- `enunciado` es el texto del ítem tal como aparece, sin su número ni viñetas.
- No inventes ítems. Las instrucciones, títulos de sección y datos del evaluado no son ítems.
- `titulo` es el título del cuestionario; si no tiene, usa null.
- `idioma` es el idioma principal del documento en código ISO 639-1 (it, es, en...).
- `total_items` es la cantidad de ítems de la lista `items`.

Reglas por tipo de ítem (`tipo`):
- `escala_likert`: afirmaciones que se responden con una escala de frecuencia o acuerdo
  (por ejemplo: Nunca, A veces, Siempre). `valor` es numérico, empezando en 0, salvo que
  el documento indique otros valores.
- `seleccion_multiple`: preguntas con opciones de las que se elige una. `valor` es la letra
  de la opción tal como aparece (A, B, C...); si las opciones no tienen letra, asígnalas en orden.
- `verdadero_falso`: afirmaciones que se responden con verdadero o falso. Las alternativas son
  `V` y `F`, con el texto en el idioma del documento.
- `desarrollo`: preguntas de respuesta abierta. `alternativas` es una lista vacía.
- `emparejamiento`: el conjunto de elementos a relacionar es UN solo ítem, con la instrucción
  como `enunciado`. `alternativas` incluye primero los elementos de la columna izquierda, con
  `valor` numérico (1, 2, 3...), y después los de la columna derecha, con `valor` en letras
  minúsculas (a, b, c...). Si el documento indica la respuesta, `respuesta_correcta` es un texto
  con los pares en el formato "1-b; 2-c; 3-a".

Respuesta correcta (`respuesta_correcta`):
- Inclúyela solo si el documento la indica (marcada, resaltada o en una clave de respuestas).
  Su valor es el `valor` de la alternativa correcta.
- Nunca resuelvas los ítems por tu cuenta. Si el documento no la indica, usa null.
- En `escala_likert` y `desarrollo` siempre es null.
""".strip()

# Los cuestionarios psicológicos tratan temas sensibles (ansiedad, autolesiones,
# pensamientos negativos). Los filtros se desactivan para no bloquear ítems legítimos.
SAFETY_SETTINGS = [
    types.SafetySetting(category=category, threshold=types.HarmBlockThreshold.OFF)
    for category in (
        types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        types.HarmCategory.HARM_CATEGORY_HARASSMENT,
    )
]


class QuestionnaireExtractor:
    """Extrae los ítems de un cuestionario con Gemini, en una sola llamada por documento.

    No depende del proveedor: recibe un `genai.Client` ya creado, con Vertex AI o con la Gemini API.
    """

    def __init__(self, client: genai.Client, settings: ExtractorSettings):
        self.client = client
        self.settings = settings
        self.config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_json_schema=Questionnaire.model_json_schema(),
            max_output_tokens=settings.MAX_OUTPUT_TOKENS,
            temperature=settings.TEMPERATURE,
            top_p=settings.TOP_P,
            seed=settings.SEED,
            safety_settings=SAFETY_SETTINGS,
        )

    def build_document_part(self, document: InputDocument) -> types.Part:
        """Convierte el documento en el contenido que recibe el modelo."""
        if document.format == DocumentFormat.PDF:
            return types.Part.from_bytes(data=document.content, mime_type=MIME_TYPES[DocumentFormat.PDF])

        # Gemini no lee .docx ni .xlsx directamente: se envían como texto.
        readers = {DocumentFormat.DOCX: docx_to_text, DocumentFormat.XLSX: xlsx_to_text}
        reader = readers.get(document.format)
        if reader is None:
            msg = f"El formato {document.format.value} no está soportado."
            raise UnsupportedFormatError(msg)

        text = reader(document.content)
        if not text:
            msg = "El documento no tiene texto."
            raise NoItemsFoundError(msg)
        return types.Part.from_text(text=text)

    async def extract(self, document: InputDocument) -> Questionnaire:
        """Envía el documento al modelo y devuelve el cuestionario validado."""
        return await self._extract_part(self.build_document_part(document))

    async def extract_sheets(self, document: InputDocument) -> list[SheetResult]:
        """Procesa cada hoja de un Excel como un cuestionario independiente, todas en paralelo.

        Las hojas vacías se omiten. El error de una hoja no afecta a las demás.
        """
        sheets = [(name, text) for name, text in xlsx_sheets_to_text(document.content) if text]
        if not sheets:
            msg = "El Excel no tiene hojas con contenido."
            raise NoItemsFoundError(msg)
        if len(sheets) > self.settings.MAX_SHEETS:
            msg = f"El Excel tiene {len(sheets)} hojas con contenido; el máximo es {self.settings.MAX_SHEETS}."
            raise TooManySheetsError(msg)

        return list(await asyncio.gather(*(self._extract_sheet(name, text) for name, text in sheets)))

    async def _extract_sheet(self, name: str, text: str) -> SheetResult:
        try:
            questionnaire = await self._extract_part(types.Part.from_text(text=text))
            return SheetResult(sheet_name=name, questionnaire=questionnaire)
        except ExtractionError as error:
            return SheetResult(sheet_name=name, error=ErrorResponse(error=error.code, detail=str(error)))
        except Exception:
            logger.exception("Error inesperado procesando la hoja %s", name)
            detail = "Ocurrió un error inesperado al procesar la hoja."
            return SheetResult(sheet_name=name, error=ErrorResponse(error=ExtractionError.code, detail=detail))

    async def _extract_part(self, part: types.Part) -> Questionnaire:
        try:
            response = await self.client.aio.models.generate_content(
                model=self.settings.GENAI_MODEL,
                contents=[part],
                config=self.config,
            )
        except errors.APIError as error:
            if error.code == 429:
                msg = "Se alcanzó el límite de uso del modelo. Intente de nuevo en unos minutos."
                raise RateLimitError(msg) from error
            if error.code == 402:
                msg = "La cuenta del proveedor del modelo no tiene crédito disponible."
                raise RateLimitError(msg) from error
            logger.error("Error del servicio del modelo: %s", error)
            msg = "El servicio del modelo no respondió correctamente."
            raise ModelServiceError(msg) from error

        finish_reason = response.candidates[0].finish_reason if response.candidates else None
        if finish_reason == types.FinishReason.MAX_TOKENS:
            msg = "El documento es demasiado grande para procesarse completo."
            raise TruncatedResponseError(msg)

        if not response.text:
            logger.error("Respuesta vacía del modelo. finish_reason=%s", finish_reason)
            msg = "El modelo no devolvió una respuesta."
            raise InvalidModelResponseError(msg)

        try:
            questionnaire = Questionnaire.model_validate_json(response.text)
        except ValidationError as error:
            logger.error("La respuesta del modelo no cumple el esquema: %s", error)
            msg = "La respuesta del modelo no cumple el esquema esperado."
            raise InvalidModelResponseError(msg) from error

        if not questionnaire.items:
            msg = "No se detectaron ítems en el documento."
            raise NoItemsFoundError(msg)

        return questionnaire
