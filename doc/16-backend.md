# 16 - Backend

Se construye un backend pequeño, para **un solo usuario**, que pueda:

- iniciar sesión;
- guardar sus cuestionarios;
- eliminar cuestionarios;
- consumir la API de cuestionarios (los extractores).

Además, el backend resuelve un riesgo que hoy existe: los extractores son públicos y cada llamada a Gemini tiene costo. Cuando el backend esté listo, solo él podrá invocarlos, y el acceso quedará protegido por usuario y contraseña.

## Plan por pasos

Cada paso se sube por separado, para que quede la trazabilidad en el historial.

| Paso | Qué se construye |
|------|------------------|
| 1 | **Hola mundo nativo de nube:** FastAPI dockerizado, Docker Compose, CI y Cloud Run. |
| 2 | **Inicio de sesión:** `POST /auth/login` devuelve un JWT; `GET /auth/me` es la primera ruta protegida. Un solo usuario, con la contraseña guardada como hash y los secretos en Secret Manager. |
| 3 | **Consumir los extractores:** `POST /v1/questionnaires/extract`, protegido, llama a `extractor-vertex` o `extractor-gemini` con un token de identidad de Google. |
| 4 | **Guardar, listar y eliminar cuestionarios**, con capas de DDD (dominio, casos de uso, repositorio, API) y Firestore como base de datos. |
| 5 | **Cerrar los extractores:** sin acceso público; solo los invoca la service account del backend. |
| 6 | **Frontend:** login, extracción a través del backend y lista de cuestionarios guardados. |

### Decisiones previas

- **Base de datos: Firestore** (se usa en el paso 4). Tiene capa gratuita y no cuesta nada sin uso; es serverless, así que no necesita conexiones ni VPC desde Cloud Run, y tiene emulador oficial para local. Cloud SQL cuesta unos USD 10 al mes como mínimo aunque no se use. Con la capa de repositorio, cambiar de base de datos no afectaría al dominio.
- **Puerto: 9090.** Cada servicio tiene el suyo, igual en todos los entornos: frontend 3000, `extractor-vertex` 8080, `extractor-gemini` 7070 y backend 9090.
- **Librería compartida:** el backend instala `libs/questionnaire-core` desde el paso 1, para reutilizar en el paso 4 los modelos `Questionnaire` e `Item` sin definirlos otra vez.

## Paso 1: hola mundo nativo de nube

Se repite el patrón de la etapa 2: el entorno funciona igual en local y en la nube desde el primer commit.

### Código

```
backend/
├── app/
│   ├── config.py      # Settings con pydantic-settings (por ahora, CORS_ORIGINS)
│   └── main.py        # FastAPI: GET / y GET /health, con CORS
├── tests/test_main.py
├── Dockerfile         # se construye desde la raíz, con la librería compartida
├── requirements.txt
└── pytest.ini
```

El CORS ya permite `GET`, `POST` y `DELETE`, que son los métodos que usarán los pasos siguientes.

### Infraestructura

- **Docker:** `docker build -f backend/Dockerfile .`, desde la raíz. El `.dockerignore` de la raíz agrega `backend/` a la lista de permitidos.
- **Docker Compose:** servicio `backend` en `9090:9090`. En modo desarrollo monta su código y el de la librería, con `--reload`.
- **CI:** `backend` se suma a la matriz de tests (`test-python`) y a la de despliegue, con `port: 9090` y `context: .`.

### Configuración en GCP

El pipeline actualiza servicios que ya existen, así que el primer despliegue se hace a mano. El backend tiene su propia service account; por ahora no necesita permisos, y en los pasos siguientes recibirá solo los que use (Secret Manager, Firestore e invocar a los extractores).

```bash
source .env.gcp

gcloud iam service-accounts create backend-runtime --display-name="backend en Cloud Run"
SA_BACKEND=backend-runtime@$GCP_PROJECT_ID.iam.gserviceaccount.com

docker build -t $REG/backend:v1 -f backend/Dockerfile .
docker push $REG/backend:v1

FRONTEND_URLS="https://frontend-yu7lpen3ba-uc.a.run.app,https://frontend-$GCP_PROJECT_NUMBER.us-central1.run.app"

gcloud run deploy backend \
  --image=$REG/backend:v1 \
  --region=us-central1 \
  --port=9090 \
  --service-account=$SA_BACKEND \
  --update-env-vars="^@^CORS_ORIGINS=$FRONTEND_URLS" \
  --allow-unauthenticated \
  --min-instances=0 --max-instances=2
```

Verificar:

```bash
curl https://backend-$GCP_PROJECT_NUMBER.us-central1.run.app/health
```

### Tests

`tests/test_main.py`: `GET /` y `GET /health` responden lo esperado. Se verificó la imagen en local: el contenedor escucha en el 9090 y `/health` responde `{"status":"ok"}`.

## Paso 2: inicio de sesión de un solo usuario

### Qué hacer, en orden

1. **Tener hecho el paso 1 en GCP:** la service account `backend-runtime` y el servicio `backend` desplegado (ver [Configuración en GCP del paso 1](#configuración-en-gcp)).
2. **Generar las credenciales** con el script y pegarlas en el `.env` local (ver [Generar las credenciales](#generar-las-credenciales)).
3. **Probar en local:** levantar el compose, hacer login en http://localhost:9090/docs (`POST /auth/login`) y llamar a `GET /auth/me` con el token, usando el botón *Authorize* de Swagger.
4. **Crear los secretos en GCP y conectarlos al servicio** (ver [Configuración en GCP](#configuración-en-gcp-1)).
5. **Verificar en Cloud Run** con el `curl` del final de esa sección.
6. **Commit, PR y merge:** a partir de ahí, el pipeline despliega el backend y conserva los secretos.

### Sin base de datos

Como hay un solo usuario fijo, no hace falta una base de datos. Bastan tres valores de configuración:

| Variable             | Contenido                                 | Local  | Cloud Run      |
|----------------------|-------------------------------------------|--------|----------------|
| `AUTH_USERNAME`      | Nombre del usuario                        | `.env` | Variable de entorno |
| `AUTH_PASSWORD_HASH` | Hash **argon2** de la contraseña          | `.env` | Secret Manager |
| `JWT_SECRET`         | Clave aleatoria para firmar los tokens    | `.env` | Secret Manager |

La contraseña nunca se guarda: solo su hash. El token **JWT** tampoco necesita base de datos, porque lleva dentro el usuario y su vencimiento, firmados; en cada petición solo se verifica la firma. La base de datos llega en el paso 4, para los cuestionarios.

### Endpoints

```
POST /auth/login   {"usuario": "...", "contrasena": "..."}  →  {"access_token": "...", "token_type": "bearer", "expires_in": 28800}
GET  /auth/me      Authorization: Bearer <token>             →  {"usuario": "..."}
```

`/auth/me` es la primera ruta protegida. La dependencia `get_current_user` (`app/auth.py`) es la que usarán todas las rutas protegidas de los pasos siguientes.

La respuesta del token usa los nombres del estándar OAuth 2.0 (`access_token`, `token_type`, `expires_in`), por eso no están en español. El resto de entradas y salidas, sí.

### Seguridad

- **Hash argon2** (`argon2-cffi`), el algoritmo recomendado para contraseñas.
- **Mismo error para usuario o contraseña incorrectos** (`credenciales_invalidas`): no se revela cuál de los dos falló.
- **Tiempo de respuesta constante:** la contraseña se verifica siempre, aunque el usuario no coincida, y el usuario se compara con `hmac.compare_digest`. Así el tiempo de respuesta tampoco revela si el usuario existe.
- **Tokens que vencen:** 8 horas por defecto (`JWT_EXPIRE_MINUTES`). Se exige que el token tenga `exp` y `sub`, y se rechaza un token sin vencimiento.
- **Algoritmo fijo** al validar (`HS256`), para que no se pueda forzar otro.

### Errores

| HTTP | `error`                   | Cuándo                                                   |
|------|---------------------------|----------------------------------------------------------|
| 401  | `credenciales_invalidas`  | Usuario o contraseña incorrectos.                        |
| 401  | `no_autenticado`          | Falta el header `Authorization: Bearer`.                 |
| 401  | `token_invalido`          | Token mal formado, firmado con otra clave o sin vencimiento. |
| 401  | `token_vencido`           | El token venció.                                         |
| 503  | `servicio_no_configurado` | Falta `AUTH_USERNAME`, `AUTH_PASSWORD_HASH` o `JWT_SECRET`. |

Los 401 incluyen el header `WWW-Authenticate: Bearer`, como indica el estándar. Los errores usan el mismo formato `{"error", "detalle"}` que los extractores (`ErrorResponse` de la librería compartida).

### Generar las credenciales

```bash
.venv/bin/python backend/scripts/hash_password.py
```

El script pide la contraseña de forma oculta, dos veces, e imprime las líneas para el `.env`:

```
AUTH_PASSWORD_HASH='$argon2id$v=19$m=65536,t=3,p=4$...'
JWT_SECRET='...'
```

El hash contiene `$`, así que en el `.env` va entre **comillas simples**: si no, Docker Compose lo interpretaría como variables. Se verificó que el contenedor recibe el hash sin cambios.

### Configuración en GCP

Los dos secretos se envían desde el `.env`, sin escribirlos en la terminal. Se ejecuta **desde la raíz del repo**:

```bash
source .env.gcp
SA_BACKEND=backend-runtime@$GCP_PROJECT_ID.iam.gserviceaccount.com

for pair in AUTH_PASSWORD_HASH:backend-password-hash JWT_SECRET:backend-jwt-secret; do
  var=${pair%%:*}; secret=${pair##*:}
  value=$(grep "^$var=" .env | cut -d= -f2- | sed "s/^'//; s/'$//")
  echo "$var: longitud ${#value}"                       # debe ser mayor que 0
  [ ${#value} -gt 0 ] || { echo "Falta $var en el .env"; break; }
  printf '%s' "$value" | gcloud secrets create $secret --data-file=-
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:$SA_BACKEND" --role=roles/secretmanager.secretAccessor
done
unset value

AUTH_USERNAME=$(grep '^AUTH_USERNAME=' .env | cut -d= -f2-)
gcloud run services update backend --region=us-central1 \
  --update-env-vars=AUTH_USERNAME=$AUTH_USERNAME \
  --set-secrets=AUTH_PASSWORD_HASH=backend-password-hash:latest,JWT_SECRET=backend-jwt-secret:latest
```

Como con la API key de Gemini, el permiso se da **sobre cada secreto**: `backend-runtime` solo puede leer esos dos.

**Problema encontrado:** el `update` falló con *"Secret .../backend-password-hash/versions/latest was not found"*. Los secretos se habían creado **vacíos**, porque el `.env` todavía no tenía las credenciales: se saltó el paso de generarlas. Es el mismo error que con la API key de Gemini. Si pasa, no hay que crear los secretos de nuevo, sino agregarles una versión cuando el `.env` esté completo:

```bash
for pair in AUTH_PASSWORD_HASH:backend-password-hash JWT_SECRET:backend-jwt-secret; do
  var=${pair%%:*}; secret=${pair##*:}
  value=$(grep "^$var=" .env | cut -d= -f2- | sed "s/^'//; s/'$//")
  echo "$var: longitud ${#value}"
  [ ${#value} -gt 0 ] && printf '%s' "$value" | gcloud secrets versions add $secret --data-file=-
done
unset value
```

Verificar:

```bash
URL=https://backend-$GCP_PROJECT_NUMBER.us-central1.run.app
TOKEN=$(curl -s -X POST $URL/auth/login -H 'Content-Type: application/json' \
  -d '{"usuario":"<usuario>","contrasena":"<contraseña>"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl $URL/auth/me -H "Authorization: Bearer $TOKEN"
```

### Tests

`tests/test_auth.py` (13 tests), con un usuario de prueba definido en `tests/conftest.py`. Los tests nunca usan las credenciales reales.

- Un login correcto devuelve un JWT válido, con el usuario y la duración configurada.
- Usuario incorrecto, contraseña incorrecta o ambos devuelven el **mismo** `401 credenciales_invalidas`.
- Un login sin configuración devuelve `503`.
- `/auth/me` con un token válido, sin token, vencido, firmado con otra clave, mal formado y sin vencimiento.

También se probó en el contenedor: login incorrecto (401), login correcto (token), `/auth/me` con token (200) y sin token (401).
