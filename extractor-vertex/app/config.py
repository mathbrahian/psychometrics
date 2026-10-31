from questionnaire_core.settings import ExtractorSettings


class Settings(ExtractorSettings):
    """Configuración de extractor-vertex: la común más los datos de Vertex AI.

    Las credenciales salen de ADC: archivo montado en local, service account del servicio en Cloud Run.
    """

    GOOGLE_CLOUD_PROJECT: str = ""
    GOOGLE_CLOUD_LOCATION: str = "global"


settings = Settings()
