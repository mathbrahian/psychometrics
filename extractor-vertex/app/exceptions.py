class ExtractionError(Exception):
    """Error base del proceso de extracción."""

    code = "error_extraccion"


class UnsupportedFormatError(ExtractionError):
    code = "formato_invalido"


class NoItemsFoundError(ExtractionError):
    code = "sin_items"


class TruncatedResponseError(ExtractionError):
    code = "documento_demasiado_grande"


class InvalidModelResponseError(ExtractionError):
    code = "respuesta_invalida"
