# 4 - Extractor Vertex

Esta etapa construye el core de la solución: un microservicio que recibe un cuestionario en PDF, Word o Excel y devuelve sus ítems en un JSON estructurado.

El foco está en tres cosas: la entrada de datos, la salida de datos y la conexión con Vertex AI.

## Alcance de esta etapa

### Entrada

- Un endpoint que recibe el archivo como `multipart/form-data`.
- Formatos soportados: `.pdf`, `.docx` y `.xlsx`.
- Validación del archivo: extensión, tipo real del contenido, tamaño máximo y que no esté vacío.
- Extracción del texto según el formato, antes de enviarlo al modelo.

### Salida

- El esquema JSON de la prueba, definido con modelos de Pydantic: `titulo`, `idioma`, `total_items` e `items`, y por cada ítem `numero`, `enunciado`, `tipo`, `alternativas` y `respuesta_correcta`.
- Tipos de ítem: `escala_likert`, `seleccion_multiple`, `verdadero_falso`, `desarrollo` y `emparejamiento`.
- Idioma detectado: al menos italiano, español e inglés.
- Respuestas de error claras para formato inválido, documento sin ítems y fallos del procesamiento.

### Conexión con Vertex AI

- Habilitar la API de Vertex AI (`aiplatform.googleapis.com`) en el proyecto.
- Dar a la identidad del servicio en Cloud Run el permiso para usar Vertex AI.
- En local, autenticarse con las credenciales de la cuenta de desarrollo, sin llaves en el repositorio.
- Pedirle al modelo una respuesta estructurada que cumpla el esquema de salida.

### Tests

- Validación del archivo de entrada.
- Esquema de salida.
- La llamada a Vertex AI se simula en los tests, para que no tengan costo ni dependan de la red.

Fuera de alcance: el backend, la base de datos y el extractor-gemini.

## Resultado esperado

Desde el frontend, o directamente contra la API, se sube un cuestionario y se recibe el JSON estructurado, tanto en local con Docker Compose como en Cloud Run.
