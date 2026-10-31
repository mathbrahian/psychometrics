from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración del servicio, leída de variables de entorno."""

    model_config = SettingsConfigDict(extra="ignore")

    CORS_ORIGINS: str = ""

    # Vertex AI. Las credenciales salen de ADC: archivo montado en local,
    # service account del servicio en Cloud Run.
    GOOGLE_CLOUD_PROJECT: str = ""
    GOOGLE_CLOUD_LOCATION: str = "global"
    GENAI_MODEL: str = "gemini-3.8-flash"
    MAX_OUTPUT_TOKENS: int = 32768
    TEMPERATURE: float = 0.0
    TOP_P: float = 0.95
    SEED: int = 0

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
