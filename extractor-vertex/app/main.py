from google import genai
from questionnaire_core.api import create_app
from questionnaire_core.extractor import QuestionnaireExtractor

from app.config import settings


def build_extractor() -> QuestionnaireExtractor:
    """Extractor con Gemini en Vertex AI (pago por uso, credenciales de GCP)."""
    client = genai.Client(
        vertexai=True,
        project=settings.GOOGLE_CLOUD_PROJECT,
        location=settings.GOOGLE_CLOUD_LOCATION,
    )
    return QuestionnaireExtractor(client=client, settings=settings)


app = create_app("extractor-vertex", settings, build_extractor)
