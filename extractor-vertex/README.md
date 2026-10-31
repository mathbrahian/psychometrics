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

## Variables de entorno

| Variable | Default | Descripción                                                    |
|----------|---------|----------------------------------------------------------------|
| `PORT`   | `8080`  | Puerto en el que escucha la API. Cloud Run lo asigna solo.     |

Para usar otro puerto en local:

```bash
docker run --rm -e PORT=9000 -p 9000:9000 extractor-vertex
```
