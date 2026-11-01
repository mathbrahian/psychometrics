from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url


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

    # Extractores. En local se llaman por el nombre del servicio del compose y sin token;
    # en Cloud Run, por su URL y con un token de identidad de Google (EXTRACTOR_AUTH=id_token).
    EXTRACTOR_VERTEX_URL: str = ""
    EXTRACTOR_GEMINI_URL: str = ""
    EXTRACTOR_AUTH: str = "none"
    EXTRACTOR_TIMEOUT_SECONDS: float = 120.0

    # Base de datos PostgreSQL. En local, el contenedor `postgres` del compose (DB_HOST);
    # en Cloud Run, Cloud SQL por socket Unix (DB_INSTANCE_CONNECTION_NAME). DB_PASSWORD sale de Secret Manager.
    DATABASE_URL: str = ""
    DB_USER: str = "app"
    DB_PASSWORD: str = ""
    DB_NAME: str = "psychometrics"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_INSTANCE_CONNECTION_NAME: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def database_url(self) -> URL:
        if self.DATABASE_URL:
            return make_url(self.DATABASE_URL)
        if self.DB_INSTANCE_CONNECTION_NAME:
            # Cloud Run monta el socket de Cloud SQL en /cloudsql/<connectionName> (--add-cloudsql-instances).
            query = {"host": f"/cloudsql/{self.DB_INSTANCE_CONNECTION_NAME}"}
            return URL.create("postgresql+psycopg", self.DB_USER, self.DB_PASSWORD, database=self.DB_NAME, query=query)
        return URL.create(
            "postgresql+psycopg", self.DB_USER, self.DB_PASSWORD, self.DB_HOST, self.DB_PORT, self.DB_NAME
        )

    @property
    def auth_configured(self) -> bool:
        return bool(self.AUTH_USERNAME and self.AUTH_PASSWORD_HASH and self.JWT_SECRET)


settings = Settings()
