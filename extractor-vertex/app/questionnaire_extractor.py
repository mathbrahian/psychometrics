import logging

from google import genai
from google.genai import types
from pydantic import ValidationError

from app.config import settings
from app.document_reader import docx_to_text
from app.exceptions import (
    InvalidModelResponseError,
    NoItemsFoundError,
    TruncatedResponseError,
    UnsupportedFormatError,
)
from app.models.input_schemas import MIME_TYPES, DocumentFormat, InputDocument
from app.models.output_schemas import Questionnaire

logger = logging.getLogger("extractor-vertex")

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
- `emparejamiento`: cada elemento de la columna izquierda es un ítem. `alternativas` son los
  elementos de la columna derecha, con `valor` en letras (A, B, C...).

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
    """Extrae los ítems de un cuestionario con Gemini en Vertex AI, en una sola llamada."""

    def __init__(self, client: genai.Client | None = None):
        self.client = client or genai.Client(
            vertexai=True,
            project=settings.GOOGLE_CLOUD_PROJECT,
            location=settings.GOOGLE_CLOUD_LOCATION,
        )
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
        if document.format == DocumentFormat.DOCX:
            text = docx_to_text(document.content)
            if not text:
                msg = "El documento no tiene texto."
                raise NoItemsFoundError(msg)
            return types.Part.from_text(text=text)

        msg = f"El formato {document.format.value} todavía no está soportado."
        raise UnsupportedFormatError(msg)

    async def extract(self, document: InputDocument) -> Questionnaire:
        """Envía el documento al modelo y devuelve el cuestionario validado."""
        response = await self.client.aio.models.generate_content(
            model=settings.GENAI_MODEL,
            contents=[self.build_document_part(document)],
            config=self.config,
        )

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
