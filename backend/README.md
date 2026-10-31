# backend

Backend de la aplicación: inicio de sesión de un usuario, gestión de sus cuestionarios y consumo de los extractores. Se construye por pasos (ver [doc/16-backend.md](../doc/16-backend.md)); por ahora es un hola mundo.

## Correr localmente

Desde la raíz del repo, porque la imagen incluye la librería compartida [`libs/questionnaire-core`](../libs/questionnaire-core):

```bash
docker build -t backend -f backend/Dockerfile .
docker run --rm -p 9090:9090 backend
```

La API queda en http://localhost:9090 (Swagger en `/docs`). Con Docker Compose se levanta junto a los demás servicios.

## Endpoints

| Método | Ruta      | Descripción         |
|--------|-----------|---------------------|
| GET    | `/`       | Hola mundo          |
| GET    | `/health` | Estado del servicio |

## Variables de entorno

| Variable       | Default | Descripción                                                  |
|----------------|---------|--------------------------------------------------------------|
| `PORT`         | `9090`  | Puerto de la API. En Cloud Run se despliega con `--port=9090`. |
| `CORS_ORIGINS` | vacío   | Orígenes permitidos, separados por coma.                     |

## Tests

```bash
pip install -e "libs/questionnaire-core[dev]" -r backend/requirements.txt
cd backend && pytest -v
```
