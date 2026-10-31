# frontend

Interfaz en React (Vite) para subir un cuestionario y ver el JSON extraído. Por ahora es un hola mundo.

## Requisitos

- Docker

## Correr localmente

Desde la carpeta `frontend/`:

```bash
docker build -t frontend .
docker run --rm -p 3000:8080 frontend
```

La app queda en http://localhost:3000.

## Cómo funciona la imagen

- **Etapa 1 (`node`):** instala dependencias y compila la app con `npm run build`.
- **Etapa 2 (`nginx`):** sirve los archivos estáticos compilados.

## Variables de entorno

| Variable | Default | Descripción                                                    |
|----------|---------|----------------------------------------------------------------|
| `PORT`   | `8080`  | Puerto en el que escucha nginx. Cloud Run lo asigna solo.      |
