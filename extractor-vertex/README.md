# extractor-vertex

API en FastAPI que recibe un cuestionario (PDF, Word o Excel) y devuelve sus ítems en JSON. Por ahora es un hola mundo.

## Requisitos

- Docker

## Correr localmente

Desde la carpeta `extractor-vertex/`:

```bash
docker build -t extractor-vertex .
docker run --rm -p 8080:8080 extractor-vertex
```

La API queda en http://localhost:8080.

## Endpoints

| Método | Ruta      | Descripción              |
|--------|-----------|--------------------------|
| GET    | `/`       | Hola mundo               |
| GET    | `/health` | Estado del servicio      |
| GET    | `/docs`   | Documentación (Swagger)  |
| POST   | `/v1/questionnaires/extract` | Recibe un cuestionario (`file`: PDF o .docx) y devuelve sus ítems en JSON |

## Variables de entorno

| Variable | Default | Descripción                                                    |
|----------|---------|----------------------------------------------------------------|
| `PORT`   | `8080`  | Puerto en el que escucha la API. Cloud Run lo asigna solo.     |
| `MAX_FILE_SIZE_MB` | `10` | Tamaño máximo del archivo subido. |
| `GOOGLE_CLOUD_PROJECT` | vacío | Proyecto de GCP de Vertex AI. |
| `GOOGLE_CLOUD_LOCATION` | `global` | Endpoint de Vertex AI. |
| `GENAI_MODEL` | `gemini-3.8-flash` | Modelo de Gemini. |
| `CORS_ORIGINS` | vacío | Orígenes permitidos separados por coma, por ejemplo `http://localhost:3000`. Vacío no permite ninguno. |

Para usar otro puerto en local:

```bash
docker run --rm -e PORT=9000 -p 9000:9000 extractor-vertex
```

## Tests

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -v
```
