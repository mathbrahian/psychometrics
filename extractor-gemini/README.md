# extractor-gemini

El mismo extractor de cuestionarios que `extractor-vertex`, pero con la **Gemini API de AI Studio**, que tiene free tier. Toda la lógica está en la librería compartida [`libs/questionnaire-core`](../libs/questionnaire-core); este servicio solo crea el cliente con una API key.

## Correr localmente

Desde la raíz del repo:

```bash
docker build -t extractor-gemini -f extractor-gemini/Dockerfile .
docker run --rm -p 7070:7070 -e GEMINI_API_KEY=<tu-api-key> extractor-gemini
```

La API queda en http://localhost:7070 (Swagger en `/docs`). Con Docker Compose se levanta junto a los demás servicios, leyendo `GEMINI_API_KEY` de `.env`.

## Endpoints

Los mismos que `extractor-vertex`: `GET /health`, `POST /v1/questionnaires/extract` y `POST /v1/questionnaires/extract-sheets`.

## Variables de entorno

| Variable          | Default            | Descripción                                                     |
|-------------------|--------------------|-----------------------------------------------------------------|
| `PORT`            | `7070`             | Puerto de la API. En Cloud Run se despliega con `--port=7070`.  |
| `GEMINI_API_KEY`  | vacío              | API key de AI Studio. En Cloud Run sale de Secret Manager. Sin ella, la extracción responde `503 servicio_no_configurado`. |
| `GENAI_MODEL`     | `gemini-3.8-flash` | Modelo de Gemini.                                               |
| `CORS_ORIGINS`    | vacío              | Orígenes permitidos, separados por coma.                        |
| `MAX_FILE_SIZE_MB`, `MAX_SHEETS`, `MAX_OUTPUT_TOKENS`, `TEMPERATURE`, `TOP_P`, `SEED` | | Igual que en `extractor-vertex`. |

## Tests

```bash
pip install -e "libs/questionnaire-core[dev]" -r extractor-gemini/requirements.txt
cd extractor-gemini && pytest -v
```
