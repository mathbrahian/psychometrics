# frontend

Interfaz en React (Vite) para subir un cuestionario y ver el JSON extraído. Por ahora es un hola mundo.

## Requisitos

- Docker

## Correr localmente

Desde la carpeta `frontend/`:

```bash
docker build -t frontend .
docker run --rm -p 3000:3000 frontend
```

La app queda en http://localhost:3000.

## Cómo funciona la imagen

- **Etapa 1 (`node`):** instala dependencias y compila la app con `npm run build`.
- **Etapa 2 (`node`):** al arrancar genera `config.js` con las variables de entorno y sirve los archivos compilados con `serve`.

## Variables de entorno

| Variable | Default | Descripción                                                    |
|----------|---------|----------------------------------------------------------------|
| `PORT`   | `3000`  | Puerto en el que escucha el servidor. En Cloud Run el servicio se despliega con `--port=3000`. |
| `BACKEND_URL` | `http://localhost:9090` | URL pública del backend. La usa el navegador, no el contenedor. |
