from questionnaire_core.settings import ExtractorSettings


class Settings(ExtractorSettings):
    """Configuración de extractor-gemini: la común más la API key de la Gemini API (AI Studio).

    La API key nunca va en el repositorio: en local sale de `.env` y en Cloud Run de Secret Manager.
    """

    GEMINI_API_KEY: str = ""


settings = Settings()
