# psychometrics
Giunti Psychometrics está llevando sus cuestionarios y pruebas de evaluación en papel a su plataforma digital de administración y corrección. Hoy ese material existe en PDF, Word o Excel, y cargarlo a mano toma horas.

## Correr localmente

Todo corre con Docker Compose. Antes de la primera vez:

```bash
# 1. Variables locales (completar GCP_PROJECT_ID)
cp .env.example .env

# 2. Credenciales de Vertex AI, en un directorio aparte para no tocar otras cuentas de gcloud
CLOUDSDK_CONFIG=~/.config/gcloud-psychometrics gcloud auth application-default login
```

Detalle en [doc/4-extractor-vertex.md](doc/4-extractor-vertex.md). Luego, desde la raíz del repo:

**Modo producción** (las mismas imágenes que van a Cloud Run):

```bash
docker compose up --build
```

**Modo desarrollo** (código montado como volumen y recarga en caliente):

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

| Servicio           | URL                        |
|--------------------|----------------------------|
| `frontend`         | http://localhost:3000      |
| `extractor-vertex` | http://localhost:8080/docs |

## Documentación y videos

- Documentación de cada etapa en [`doc/`](doc/).
- Videos de avance en [`doc/videos.md`](doc/videos.md).
