// Convierte una respuesta de error del backend en un mensaje para el usuario.
//
// El backend y los extractores responden { error, detalle } con un detalle ya pensado para el usuario
// (por ejemplo, "El formato '.doc' no está soportado."). FastAPI responde los errores de validación
// como { detail: [...] }. Para cualquier otro caso se usa un mensaje según el código HTTP.

const STATUS_MESSAGES = {
  400: 'La solicitud no es válida.',
  401: 'La sesión no es válida o venció. Inicie sesión de nuevo.',
  404: 'No se encontró lo que se buscaba.',
  413: 'El archivo es demasiado grande.',
  415: 'El formato del archivo no está soportado.',
  422: 'Los datos enviados no son válidos.',
  429: 'Se alcanzó el límite de uso. Intente de nuevo en unos minutos.',
  502: 'El servicio de extracción no respondió correctamente. Intente de nuevo.',
  503: 'El servicio no está disponible en este momento. Intente más tarde.',
  504: 'El procesamiento tardó demasiado. Intente con un documento más pequeño o más tarde.',
}

export const NETWORK_ERROR = 'No se pudo conectar con el servidor. Revise su conexión o intente más tarde.'

export function errorMessage(status, data) {
  if (data?.detalle) return data.detalle
  if (status === 422 && Array.isArray(data?.detail)) {
    const fields = data.detail.map((issue) => issue.loc?.at(-1)).filter(Boolean)
    return fields.length ? `${STATUS_MESSAGES[422]} Revise: ${fields.join(', ')}.` : STATUS_MESSAGES[422]
  }
  return STATUS_MESSAGES[status] ?? `Ocurrió un error inesperado (HTTP ${status}).`
}

// Validación previa en el navegador: evita subir archivos que el backend rechazaría.
const MAX_FILE_SIZE_MB = 10
const EXTENSIONS = { extract: ['pdf', 'docx', 'xlsx'], 'extract-sheets': ['xlsx'] }

export function validateFile(file, endpoint) {
  const extension = file.name.split('.').pop().toLowerCase()
  const allowed = EXTENSIONS[endpoint]
  if (!allowed.includes(extension)) {
    const list = allowed.map((value) => `.${value}`).join(', ')
    return `El formato '.${extension}' no está soportado para esta opción. Formatos válidos: ${list}.`
  }
  if (file.size === 0) return 'El archivo está vacío.'
  if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) return `El archivo supera el tamaño máximo de ${MAX_FILE_SIZE_MB} MB.`
  return null
}
