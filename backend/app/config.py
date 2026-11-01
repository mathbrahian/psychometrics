from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración del backend, leída de variables de entorno."""

    model_config = SettingsConfigDict(extra="ignore")

    CORS_ORIGINS: str = ""

    # Usuario único de la aplicación. La contraseña se guarda solo como hash (argon2).
    # En local salen de .env; en Cloud Run, el hash y JWT_SECRET salen de Secret Manager.
    AUTH_USERNAME: str = ""
    AUTH_PASSWORD_HASH: str = ""
    JWT_SECRET: str = ""
    JWT_EXPIRE_MINUTES: int = 480

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def auth_configured(self) -> bool:
        return bool(self.AUTH_USERNAME and self.AUTH_PASSWORD_HASH and self.JWT_SECRET)


settings = Settings()
