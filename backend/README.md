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
| POST   | `/v1/questionnaires/extract?proveedor=gemini\|vertex` | Extrae un cuestionario con el extractor elegido (por defecto `gemini`). Requiere sesión. |
| POST   | `/v1/questionnaires/extract-sheets?proveedor=gemini\|vertex` | Procesa todas las hojas de un Excel. Requiere sesión. |
| POST   | `/v1/questionnaires` | Guarda un cuestionario: `{"proveedor", "archivo_origen", "cuestionario"}`. Requiere sesión. |
| GET    | `/v1/questionnaires` | Lista los cuestionarios guardados, sin sus ítems. Requiere sesión. |
| GET    | `/v1/questionnaires/{id}` | Cuestionario guardado completo. Requiere sesión. |
| DELETE | `/v1/questionnaires/{id}` | Elimina un cuestionario guardado. Requiere sesión. |

## Variables de entorno

| Variable       | Default | Descripción                                                  |
|----------------|---------|--------------------------------------------------------------|
| `PORT`         | `9090`  | Puerto de la API. En Cloud Run se despliega con `--port=9090`. |
| `CORS_ORIGINS` | vacío   | Orígenes permitidos, separados por coma.                     |
| `AUTH_USERNAME` | vacío  | Usuario único de la aplicación.                              |
| `AUTH_PASSWORD_HASH` | vacío | Hash argon2 de la contraseña. En Cloud Run sale de Secret Manager. |
| `JWT_SECRET`   | vacío   | Clave para firmar los tokens. En Cloud Run sale de Secret Manager. |
| `JWT_EXPIRE_MINUTES` | `480` | Duración del token (8 horas).                              |
| `EXTRACTOR_VERTEX_URL` | vacío | URL de `extractor-vertex`. En local, `http://extractor-vertex:8080`. |
| `EXTRACTOR_GEMINI_URL` | vacío | URL de `extractor-gemini`. En local, `http://extractor-gemini:7070`. |
| `EXTRACTOR_AUTH` | `none` | `id_token` en Cloud Run: envía un token de identidad de Google a los extractores. |
| `EXTRACTOR_TIMEOUT_SECONDS` | `120` | Tiempo máximo de espera de un extractor. |
| `DB_HOST`, `DB_PORT` | `localhost`, `5432` | PostgreSQL local. En el compose, `postgres`. |
| `DB_USER`, `DB_NAME` | `app`, `psychometrics` | Usuario y base de datos. |
| `DB_PASSWORD` | vacío | Contraseña. En Cloud Run sale de Secret Manager. |
| `DB_INSTANCE_CONNECTION_NAME` | vacío | En Cloud Run: el `connectionName` de Cloud SQL. Si está definido, se conecta por el socket `/cloudsql/<connectionName>`. |
| `DATABASE_URL` | vacío | URL completa de SQLAlchemy. Si está definida, reemplaza a las anteriores. |

Al arrancar, el contenedor aplica las migraciones pendientes (`alembic upgrade head`) y después levanta la API.

Si falta alguna de las tres primeras, `/auth/login` responde `503 servicio_no_configurado`.

Peticiones de ejemplo en [`requests.http`](requests.http) (REST Client de VS Code).

Para generar el hash y la clave (la contraseña se pide de forma oculta):

```bash
.venv/bin/python backend/scripts/hash_password.py
```

## Tests

```bash
pip install -e "libs/questionnaire-core[dev]" -r backend/requirements.txt
cd backend && pytest -v
```
