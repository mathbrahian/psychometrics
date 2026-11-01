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
