from google import genai
from questionnaire_core.api import create_app
from questionnaire_core.exceptions import ServiceNotConfiguredError
from questionnaire_core.extractor import QuestionnaireExtractor

from app.config import settings


def build_extractor() -> QuestionnaireExtractor:
    """Extractor con la Gemini API de AI Studio (free tier, API key)."""
    if not settings.GEMINI_API_KEY:
        msg = "extractor-gemini no tiene configurada la variable GEMINI_API_KEY."
        raise ServiceNotConfiguredError(msg)
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return QuestionnaireExtractor(client=client, settings=settings)


app = create_app("extractor-gemini", settings, build_extractor)
