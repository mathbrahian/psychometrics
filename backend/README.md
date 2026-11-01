# backend

Backend de la aplicación: inicio de sesión de un usuario, gestión de sus cuestionarios y consumo de los extractores. Se construye por pasos (ver [doc/16-backend.md](../doc/16-backend.md)).

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
| POST   | `/auth/login` | Recibe `{"usuario", "contrasena"}` y devuelve un JWT (`access_token`) |
| GET    | `/auth/me` | Usuario autenticado. Requiere `Authorization: Bearer <token>` |

## Variables de entorno

| Variable       | Default | Descripción                                                  |
|----------------|---------|--------------------------------------------------------------|
| `PORT`         | `9090`  | Puerto de la API. En Cloud Run se despliega con `--port=9090`. |
| `CORS_ORIGINS` | vacío   | Orígenes permitidos, separados por coma.                     |
| `AUTH_USERNAME` | vacío  | Usuario único de la aplicación.                              |
| `AUTH_PASSWORD_HASH` | vacío | Hash argon2 de la contraseña. En Cloud Run sale de Secret Manager. |
| `JWT_SECRET`   | vacío   | Clave para firmar los tokens. En Cloud Run sale de Secret Manager. |
| `JWT_EXPIRE_MINUTES` | `480` | Duración del token (8 horas).                              |

Si falta alguna de las tres primeras, `/auth/login` responde `503 servicio_no_configurado`.

Para generar el hash y la clave (la contraseña se pide de forma oculta):

```bash
.venv/bin/python backend/scripts/hash_password.py
```

## Tests

```bash
pip install -e "libs/questionnaire-core[dev]" -r backend/requirements.txt
cd backend && pytest -v
```
