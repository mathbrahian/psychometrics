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
