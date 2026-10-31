# psychometrics
Giunti Psychometrics está llevando sus cuestionarios y pruebas de evaluación en papel a su plataforma digital de administración y corrección. Hoy ese material existe en PDF, Word o Excel, y cargarlo a mano toma horas.

## Correr localmente

Todo corre con Docker Compose. Desde la raíz del repo:

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
