from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración del backend, leída de variables de entorno."""

    model_config = SettingsConfigDict(extra="ignore")

    CORS_ORIGINS: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
