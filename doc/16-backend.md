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
| 4 | **Guardar, listar y eliminar cuestionarios**, con capas de DDD (dominio, casos de uso, repositorio, API) y PostgreSQL en Cloud SQL. |
| 5 | **Cerrar los extractores:** sin acceso público; solo los invoca la service account del backend. |
| 6 | **Frontend:** login, extracción a través del backend y lista de cuestionarios guardados. |

### Decisiones previas

- **Base de datos: Cloud SQL con PostgreSQL** (se usa en el paso 4). En un principio se eligió Firestore por costo, pero se cambió a PostgreSQL (ver la decisión en el paso 4).
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

### Despliegue

El código del paso 2 llega a Cloud Run con el merge a `main`. Antes del merge, el servicio ya tenía los secretos configurados, pero seguía ejecutando la imagen del paso 1, así que `/auth/login` respondía `404`. Es lo esperado: los secretos y el código se despliegan por caminos distintos.

Verificado después del pipeline (los 5 jobs de tests y los 4 despliegues en verde):

| Prueba                          | Respuesta                    |
|---------------------------------|------------------------------|
| Login con credenciales falsas   | `401 credenciales_invalidas` |
| `/auth/me` sin token            | `401 no_autenticado`         |
| `/auth/me` con un token falso   | `401 token_invalido`         |

Que el login falso responda `credenciales_invalidas` y no `503 servicio_no_configurado` confirma que el servicio lee bien el usuario, el hash y la clave desde Secret Manager.

## Paso 3: el backend consume los extractores

### Endpoints

```
POST /v1/questionnaires/extract?proveedor=gemini|vertex          → un cuestionario
POST /v1/questionnaires/extract-sheets?proveedor=gemini|vertex   → un resultado por hoja de Excel
```

- **Requieren sesión** (`Depends(get_current_user)`). Sin token responden `401` y no se llama al extractor.
- **El proveedor por defecto es `gemini`.** Un proveedor desconocido responde `422`.
- **El backend es un intermediario:** reenvía el archivo al extractor y devuelve su respuesta **sin cambios**, con su código HTTP. Los errores del extractor (`415`, `422`, `429`...) llegan tal cual, y la validación no se duplica.

### `ExtractorClient` (`app/extractors.py`)

| Situación                                                  | Respuesta del backend          |
|------------------------------------------------------------|--------------------------------|
| El extractor responde (con éxito o con error)              | Su código HTTP y su JSON       |
| El extractor tarda más de `EXTRACTOR_TIMEOUT_SECONDS` (120 s) | `504 tiempo_agotado`        |
| No se puede conectar con el extractor                      | `502 extractor_no_disponible`  |
| Responde algo que no es JSON (por ejemplo, el 403 en HTML de Cloud Run si falta el permiso) | `502 extractor_no_disponible`, con el código HTTP en el detalle |
| La URL del extractor no está configurada                   | `503 servicio_no_configurado`  |

### Autenticación con los extractores

| Entorno   | URL del extractor                     | Autenticación                                   |
|-----------|---------------------------------------|-------------------------------------------------|
| Local     | `http://extractor-gemini:7070` (nombre del servicio del compose) | Ninguna (`EXTRACTOR_AUTH=none`) |
| Cloud Run | `https://extractor-gemini-<PROJECT_NUMBER>.us-central1.run.app` | Token de identidad de Google (`EXTRACTOR_AUTH=id_token`) |

En Cloud Run, antes de cada llamada, el backend pide a Google un **token de identidad** de su service account (`backend-runtime`) con la URL del extractor como *audience* (`google.oauth2.id_token.fetch_id_token`), y lo envía en `Authorization: Bearer`. Cloud Run verifica ese token y que `backend-runtime` tenga `roles/run.invoker` sobre el extractor. La llamada a Google es síncrona, por eso se ejecuta con `asyncio.to_thread` para no bloquear el servidor.

En local la llamada la hace el contenedor del backend, no el navegador, así que se usa el **nombre del servicio** del compose y no `localhost`.

### Prueba de punta a punta en local

Con el backend y `extractor-gemini` en la misma red Docker, y llamada real a la Gemini API:

| Prueba                                     | Resultado                                  |
|--------------------------------------------|--------------------------------------------|
| Extraer sin iniciar sesión                 | `401 no_autenticado`                       |
| Login y extracción con `proveedor=gemini`  | `200`, idioma `es`, 3 ítems                |
| Archivo `.doc`                             | `415 formato_invalido`, reenviado del extractor |
| Extractor no disponible (`vertex` apagado) | `502 extractor_no_disponible`              |

### Tests

`tests/test_extraction.py` (14 tests). Los extractores se simulan con `httpx.MockTransport`:

- sin login, `401`, sin llamar al extractor;
- `gemini` por defecto, y cada combinación de proveedor y endpoint va a la URL correcta;
- el archivo se reenvía completo;
- proveedor desconocido, `422`;
- los errores del extractor se devuelven sin cambios;
- tiempo agotado (`504`), extractor caído (`502`), respuesta no JSON (`502`) y extractor sin configurar (`503`);
- en Cloud Run se envía el token de identidad con la URL del extractor como *audience*; en local no se envía.

## Paso 6, versión en crudo: el frontend usa el backend

Se adelantó una versión mínima del paso 6, para que la app siga funcionando con los extractores cerrados. `frontend/src/App.jsx`:

1. **Formulario de inicio de sesión:** usuario y contraseña contra `POST /auth/login`. El token queda en memoria, y **Cerrar sesión** lo descarta.
2. **Extracción:** elige el proveedor (Gemini API o Vertex AI) y el modo (un cuestionario o todas las hojas del Excel), sube el archivo con el token y muestra la respuesta en crudo.

La configuración en tiempo de ejecución pasa de `EXTRACTOR_VERTEX_URL` a **`BACKEND_URL`** (`config.js`, `docker-entrypoint.sh`, `vite.config.js`, `Dockerfile` y compose). El frontend ya no conoce las URLs de los extractores.

## Paso 4: base de datos en Cloud SQL

### Decisión: PostgreSQL en lugar de Firestore

| | Cloud SQL (PostgreSQL) | Firestore |
|---|---|---|
| Costo | ~USD 10 al mes encendida; centavos detenida | Gratis en este volumen |
| Configuración | Instancia, base, usuario y conexión | Casi ninguna |
| Qué muestra | SQL, ORM (SQLAlchemy), migraciones (Alembic), transacciones, DDD con repositorio | NoSQL serverless |

Se eligió **PostgreSQL** porque la prueba es para *Backend Developer Python* y el stack relacional es lo que se espera ver en un backend. Firestore ganaba en costo y simplicidad, y el costo se controla deteniendo la instancia cuando no se usa.

El cuestionario es un documento anidado (ítems con alternativas). Se guarda **completo en una columna JSONB**, y aparte, en columnas normales, los datos que se listan o filtran (título, idioma, cantidad de ítems, proveedor, archivo de origen y fecha). No se normalizan los ítems en tablas separadas: se guarda el resultado tal como sale del extractor.

### Instancia

La configuración más barata:

| Opción | Valor | Motivo |
|---|---|---|
| Motor | PostgreSQL 17 | |
| Edición | `ENTERPRISE` | *Enterprise Plus* no permite núcleo compartido y es mucho más cara |
| Tipo | `db-f1-micro` | Núcleo compartido, el más barato |
| Disco | HDD, 10 GB, sin crecimiento automático | El mínimo |
| Disponibilidad | Una sola zona | Sin alta disponibilidad |
| Backups | Desactivados | Datos inventados; en producción se activarían |

```bash
source .env.gcp

gcloud services enable sqladmin.googleapis.com

gcloud sql instances create psychometrics-db \
  --database-version=POSTGRES_17 \
  --edition=ENTERPRISE \
  --tier=db-f1-micro \
  --region=us-central1 \
  --availability-type=zonal \
  --storage-type=HDD \
  --storage-size=10GB \
  --no-storage-auto-increase \
  --no-backup

gcloud sql databases create psychometrics --instance=psychometrics-db
```

### Usuario de la aplicación

La contraseña se genera aleatoria y va **directo a Secret Manager**: no aparece en pantalla, en archivos ni en el historial.

```bash
DB_PASS=$(openssl rand -base64 32 | tr -d '\n/+=')
gcloud sql users create app --instance=psychometrics-db --password="$DB_PASS"
printf '%s' "$DB_PASS" | gcloud secrets create backend-db-password --data-file=-
unset DB_PASS
```

### Permisos de `backend-runtime`

```bash
SA_BACKEND=backend-runtime@$GCP_PROJECT_ID.iam.gserviceaccount.com

gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$SA_BACKEND" --role=roles/cloudsql.client --condition=None

gcloud secrets add-iam-policy-binding backend-db-password \
  --member="serviceAccount:$SA_BACKEND" --role=roles/secretmanager.secretAccessor
```

`roles/cloudsql.client` permite conectarse a la instancia; la contraseña se lee solo de su secreto.

### Conexión

- **Cloud Run:** el backend se conecta con `--add-cloudsql-instances`, que monta un socket Unix seguro en `/cloudsql/<connectionName>`. No hace falta abrir la IP pública ni configurar una VPC.
- **Red:** la instancia tiene IP pública, pero **sin redes autorizadas**, así que nadie puede conectarse directamente. Para administrarla desde la máquina local se usa el Cloud SQL Auth Proxy.
- **Local:** Docker Compose levanta su propio PostgreSQL. En desarrollo no se usa la instancia de la nube ni se paga por ella.

### Verificar

```bash
gcloud sql instances describe psychometrics-db --format="value(state,settings.tier,connectionName)"
gcloud secrets versions list backend-db-password
```

### Detener y encender

Detenida, la instancia solo cobra el disco (centavos al mes):

```bash
gcloud sql instances patch psychometrics-db --activation-policy=NEVER    # detener
gcloud sql instances patch psychometrics-db --activation-policy=ALWAYS   # encender
```

### Código: capas de DDD

```
backend/app/questionnaires/
├── domain.py           # Dominio: entidad SavedQuestionnaire y contrato QuestionnaireRepository
├── service.py          # Aplicación: casos de uso (guardar, listar, ver, eliminar)
├── sql_repository.py   # Infraestructura: tabla QuestionnaireRow y repositorio con SQLAlchemy
├── schemas.py          # API: entrada y salida en español (alias de Pydantic)
└── router.py           # API: endpoints protegidos
backend/app/db.py       # Engine y sesión de SQLAlchemy
backend/migrations/     # Alembic
```

| Capa              | Depende de                  | No sabe de                       |
|-------------------|-----------------------------|----------------------------------|
| Dominio           | `questionnaire_core` (el modelo `Questionnaire`) | FastAPI, SQLAlchemy, la base de datos |
| Aplicación        | Dominio                     | FastAPI, SQLAlchemy              |
| Infraestructura   | Dominio, SQLAlchemy         | FastAPI                          |
| API               | Aplicación, infraestructura | —                                |

- **El dominio define el contrato** del repositorio (`QuestionnaireRepository`, un `Protocol`) y la infraestructura lo implementa. Cambiar de base de datos solo afectaría a `sql_repository.py`.
- **La entidad** `SavedQuestionnaire` guarda el `Questionnaire` de la librería compartida, el proveedor y el archivo de origen. Título, idioma y cantidad de ítems se **derivan** del cuestionario, así que no pueden quedar desincronizados.
- **`Provider`** (`vertex` o `gemini`) se define una sola vez en el dominio y lo usan también los endpoints de extracción.

### Endpoints

Todos requieren sesión iniciada.

| Método | Ruta                       | Respuesta |
|--------|----------------------------|-----------|
| POST   | `/v1/questionnaires`       | `201` con el cuestionario guardado |
| GET    | `/v1/questionnaires`       | `200` con la lista, del más reciente al más antiguo, **sin ítems** |
| GET    | `/v1/questionnaires/{id}`  | `200` con el cuestionario completo, o `404 cuestionario_no_encontrado` |
| DELETE | `/v1/questionnaires/{id}`  | `204`, o `404 cuestionario_no_encontrado` |

```json
POST /v1/questionnaires
{ "proveedor": "gemini", "archivo_origen": "cuestionario.docx", "cuestionario": { "titulo": "...", "idioma": "es", "total_items": 3, "items": [...] } }

→ 201
{ "id": "...", "titulo": "...", "idioma": "es", "total_items": 3, "proveedor": "gemini",
  "archivo_origen": "cuestionario.docx", "creado_en": "2026-11-01T...", "cuestionario": { ... } }
```

El cuestionario recibido se valida con el mismo esquema de la librería compartida, así que no se puede guardar un JSON que no cumpla el formato de la prueba (`422`).

Si la base de datos no responde, los endpoints devuelven `503 base_de_datos_no_disponible`.

### Tabla y migraciones

`QuestionnaireRow` usa `JSON().with_variant(JSONB(), "postgresql")`: **JSONB** en PostgreSQL y JSON genérico en otros motores. Así los tests corren sobre SQLite en memoria, que es rápido y no necesita servidor, y la base real usa JSONB.

Las migraciones se manejan con **Alembic**. La primera (`0001_create_questionnaires`) crea la tabla y un índice por `created_at`, que es el orden de la lista. La URL de conexión no está en `alembic.ini`: sale de `app.config`, igual que en la API.

**El contenedor aplica las migraciones al arrancar** (`alembic upgrade head && uvicorn ...`). Si ya están aplicadas, no hace nada. Con una sola instancia es suficiente; con muchas instancias arrancando a la vez convendría moverlas a un Cloud Run Job.

**Problema encontrado:** la primera vez, el contenedor no arrancó con *"No module named 'app'"*. El comando `alembic` no agrega la carpeta actual al `sys.path`, así que `migrations/env.py` no encontraba el paquete. Se resolvió con `prepend_sys_path = .` en `alembic.ini`.

### Conexión

| Entorno   | Cómo se conecta                                         | Variables |
|-----------|---------------------------------------------------------|-----------|
| Local     | Contenedor `postgres:17-alpine` del compose, por TCP    | `DB_HOST=postgres`, `DB_PASSWORD=app` |
| Cloud Run | Cloud SQL por socket Unix (`/cloudsql/<connectionName>`) | `DB_INSTANCE_CONNECTION_NAME`, `DB_PASSWORD` desde Secret Manager |

En el compose, el backend espera a que PostgreSQL esté listo (`healthcheck` con `pg_isready`). Los datos locales viven en el volumen `postgres-data`. En modo desarrollo también se monta `backend/migrations`.

### Configuración en Cloud Run

**Debe hacerse antes del merge.** El contenedor aplica las migraciones al arrancar: sin la configuración de la base, no arranca, y el despliegue falla (Cloud Run mantiene la versión anterior).

```bash
source .env.gcp
CONN=$(gcloud sql instances describe psychometrics-db --format="value(connectionName)")

gcloud run services update backend --region=us-central1 \
  --add-cloudsql-instances=$CONN \
  --update-env-vars=DB_INSTANCE_CONNECTION_NAME=$CONN,DB_USER=app,DB_NAME=psychometrics \
  --update-secrets=DB_PASSWORD=backend-db-password:latest
```

Se usa **`--update-secrets`** y no `--set-secrets`: `--set-secrets` reemplazaría todos los secretos del servicio y borraría `AUTH_PASSWORD_HASH` y `JWT_SECRET`.

Mientras se ejecuta este `update`, el servicio todavía corre la imagen anterior, que no usa la base: el cambio no afecta nada hasta el merge.

### Verificación

En local, contra PostgreSQL 17 real:

| Prueba                          | Resultado                                         |
|---------------------------------|---------------------------------------------------|
| Arranque                        | Alembic aplica `0001`; luego arranca la API       |
| Guardar el caso `03-tipo-pdf`   | `201`, 12 ítems                                   |
| Listar                          | Un elemento, sin ítems                            |
| Ver                             | El cuestionario es igual al JSON original         |
| Eliminar                        | `204`; la lista queda vacía                       |
| Tipos en PostgreSQL             | `content: jsonb`, `id: uuid`, `created_at: timestamptz` |
| Reinicio del contenedor         | No vuelve a migrar                                |

### Tests

- `tests/test_questionnaires.py` (14 tests): guardar, listar ordenado y sin ítems, ver, eliminar, `404` con un id desconocido, `422` con un id inválido, con un cuestionario inválido o con un proveedor desconocido, y `401` en todos los endpoints sin sesión. Usan SQLite en memoria.
- `tests/test_migrations.py`: la migración crea la tabla con sus columnas y el `downgrade` la elimina.

## Plan: que solo el backend consuma los extractores

**Objetivo:** que nadie, ni el frontend ni alguien con curl o Postman, pueda llamar a `extractor-vertex` ni a `extractor-gemini` directamente. Solo el backend podrá hacerlo, y el backend exige iniciar sesión. Así se elimina el riesgo de que un tercero consuma la cuota o el crédito de Gemini.

### Nivel de cierre elegido: IAM

| Quién llama al extractor                                   | Resultado    |
|------------------------------------------------------------|--------------|
| Backend (service account `backend-runtime`, con token de identidad) | ✅ 200 |
| Frontend desde el navegador                                | ❌ 403       |
| Cualquier persona con curl o Postman                       | ❌ 403       |
| El dueño del proyecto con un token de su cuenta (`gcloud auth print-identity-token`) | ✅ 200, acceso de administrador para depurar |

Se descartó por ahora cerrar también la red (`--ingress=internal` en los extractores más Direct VPC egress en el backend). Bloquearía incluso al dueño del proyecto desde afuera, pero exige configurar la VPC y complica la depuración. Se puede agregar después sin cambiar código.

### Orden: 3 → 6 → 5

El orden importa:

- **El backend tiene que saber llamar a los extractores con token (paso 3)** antes de cerrarlos. Si no, al cerrarlos el backend también recibiría 403.
- **El frontend tiene que pasar a usar el backend (paso 6)** antes de cerrarlos. Si no, la app dejaría de funcionar en cuanto se cierren.
- **El cierre (paso 5)** va al final, cuando ya nada depende del acceso público.

### Paso 3: el backend llama a los extractores

Código: endpoints protegidos `POST /v1/questionnaires/extract` y `POST /v1/questionnaires/extract-sheets`, con un parámetro `proveedor` (`vertex` o `gemini`). Reenvían el archivo al extractor y, en Cloud Run, envían un token de identidad de Google en cada llamada.

Configuración del servicio `backend`, una sola vez:

```bash
source .env.gcp

gcloud run services update backend --region=us-central1 --update-env-vars=\
EXTRACTOR_VERTEX_URL=https://extractor-vertex-$GCP_PROJECT_NUMBER.us-central1.run.app,\
EXTRACTOR_GEMINI_URL=https://extractor-gemini-$GCP_PROJECT_NUMBER.us-central1.run.app,\
EXTRACTOR_AUTH=id_token
```

En local, el compose define las URLs por nombre de servicio (`http://extractor-gemini:7070`) y `EXTRACTOR_AUTH=none`, porque en local no hay tokens de identidad.

Verificar, con el `$TOKEN` del login:

```bash
URL=https://backend-$GCP_PROJECT_NUMBER.us-central1.run.app
curl -F "file=@examples/01-tipo-doc/cuestionario.docx" "$URL/v1/questionnaires/extract?proveedor=gemini" \
  -H "Authorization: Bearer $TOKEN"
```

### Paso 6: el frontend usa el backend

Código: pantalla de login y llamadas al backend, con el token, en lugar de al extractor.

Configuración del servicio `frontend`, una sola vez. El CORS del backend ya permite las dos URLs del frontend desde el paso 1:

```bash
gcloud run services update frontend --region=us-central1 \
  --update-env-vars=BACKEND_URL=https://backend-$GCP_PROJECT_NUMBER.us-central1.run.app
```

Verificar en el navegador: iniciar sesión, subir un archivo y ver el resultado.

### Paso 5: cerrar los extractores

Se ejecuta **después** de verificar los pasos 3 y 6 en Cloud Run:

```bash
source .env.gcp
SA_BACKEND=backend-runtime@$GCP_PROJECT_ID.iam.gserviceaccount.com

for s in extractor-vertex extractor-gemini; do
  # 1. Solo el backend puede invocar el extractor
  gcloud run services add-iam-policy-binding $s --region=us-central1 \
    --member="serviceAccount:$SA_BACKEND" --role=roles/run.invoker

  # 2. Se quita el acceso público
  gcloud run services remove-iam-policy-binding $s --region=us-central1 \
    --member=allUsers --role=roles/run.invoker
done
```

El orden dentro del bucle evita un corte: primero se da el permiso al backend y después se quita el público.

El pipeline no vuelve a abrir los extractores: `gcloud run deploy` sin `--allow-unauthenticated` conserva los permisos del servicio.

Verificar (el cambio de permisos puede tardar uno o dos minutos):

```bash
for s in extractor-vertex extractor-gemini; do
  U=https://$s-$GCP_PROJECT_NUMBER.us-central1.run.app

  # Sin token: debe responder 403
  echo "$s sin token: $(curl -s -o /dev/null -w '%{http_code}' $U/health)"

  # Con un token de la cuenta del dueño del proyecto: debe responder 200
  echo "$s con token de administrador: $(curl -s -o /dev/null -w '%{http_code}' \
    -H "Authorization: Bearer $(gcloud auth print-identity-token)" $U/health)"
done

# A través del backend: debe seguir funcionando
curl -F "file=@examples/01-tipo-doc/cuestionario.docx" "$URL/v1/questionnaires/extract?proveedor=gemini" \
  -H "Authorization: Bearer $TOKEN"
```

Opcional, una vez cerrados: los extractores ya no reciben llamadas del navegador, así que su `CORS_ORIGINS` deja de ser necesario.

```bash
for s in extractor-vertex extractor-gemini; do
  gcloud run services update $s --region=us-central1 --remove-env-vars=CORS_ORIGINS
done
```

### Volver atrás

Si algo falla después de cerrarlos, se vuelve a abrir un extractor con un comando:

```bash
gcloud run services add-iam-policy-binding extractor-gemini --region=us-central1 \
  --member=allUsers --role=roles/run.invoker
```
