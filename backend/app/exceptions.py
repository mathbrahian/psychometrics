class BackendError(Exception):
    """Error base del backend. `code` y `status_code` definen la respuesta de la API."""

    code = "error_backend"
    status_code = 500


class InvalidCredentialsError(BackendError):
    code = "credenciales_invalidas"
    status_code = 401


class NotAuthenticatedError(BackendError):
    code = "no_autenticado"
    status_code = 401


class InvalidTokenError(BackendError):
    code = "token_invalido"
    status_code = 401


class ExpiredTokenError(BackendError):
    code = "token_vencido"
    status_code = 401


class AuthNotConfiguredError(BackendError):
    code = "servicio_no_configurado"
    status_code = 503


class ExtractorUnavailableError(BackendError):
    code = "extractor_no_disponible"
    status_code = 502


class ExtractorTimeoutError(BackendError):
    code = "tiempo_agotado"
    status_code = 504


class ExtractorNotConfiguredError(BackendError):
    code = "servicio_no_configurado"
    status_code = 503


class QuestionnaireNotFoundError(BackendError):
    code = "cuestionario_no_encontrado"
    status_code = 404


class DatabaseUnavailableError(BackendError):
    code = "base_de_datos_no_disponible"
    status_code = 503
