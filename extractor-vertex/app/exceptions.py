class ExtractionError(Exception):
    """Error base del proceso de extracción. `code` y `status_code` definen la respuesta de la API."""

    code = "error_extraccion"
    status_code = 500


class UnsupportedFormatError(ExtractionError):
    code = "formato_invalido"
    status_code = 415


class EmptyFileError(ExtractionError):
    code = "archivo_vacio"
    status_code = 400


class FileTooLargeError(ExtractionError):
    code = "archivo_demasiado_grande"
    status_code = 413


class NoItemsFoundError(ExtractionError):
    code = "sin_items"
    status_code = 422


class TruncatedResponseError(ExtractionError):
    code = "documento_demasiado_grande"
    status_code = 422


class InvalidModelResponseError(ExtractionError):
    code = "respuesta_invalida"
    status_code = 502


class TooManySheetsError(ExtractionError):
    code = "demasiadas_hojas"
    status_code = 413
