# 14 - Extractor Gemini

La prueba pide un LLM **sin costo (free tier)**, y Vertex AI se paga por uso. Esta etapa agrega `extractor-gemini`: el mismo extractor, pero con la **Gemini API de AI Studio**, que tiene free tier. `extractor-vertex` se mantiene, así que la solución puede comparar los dos proveedores con los mismos `examples/`.

Para no duplicar código, toda la lógica común se movió a una **librería compartida** dentro del monorepo.

## Arquitectura

```
psychometrics/
├── libs/
│   └── questionnaire-core/      # librería compartida: modelos, validación, lectores, prompt, extractor y API
├── extractor-vertex/            # Vertex AI   (puerto 8080): config + cliente con credenciales de GCP
├── extractor-gemini/            # Gemini API  (puerto 7070): config + cliente con API key
└── frontend/                    # React       (puerto 3000)
```

Cada extractor tiene solo dos archivos de código:

- `app/config.py`: la configuración común (`ExtractorSettings`) más la de su proveedor.
- `app/main.py`: crea su cliente de `google-genai` y la API con `create_app`.

```python
# extractor-vertex
genai.Client(vertexai=True, project=..., location=...)

# extractor-gemini
genai.Client(api_key=settings.GEMINI_API_KEY)
```

Funciona porque el SDK `google-genai` es el mismo para los dos proveedores. Solo cambia cómo se crea el cliente; el prompt, el esquema, la validación y los endpoints son idénticos.

## Librería `questionnaire-core`

### Por qué una librería local y no un paquete desde GitHub

Se evaluó instalarla desde GitHub (`pip install git+https://...#subdirectory=...`). Se descartó porque, dentro del mismo monorepo:

- un cambio en la librería obligaría a hacer commit, push y actualizar la referencia en cada servicio antes de poder usarlo;
- en un PR que cambia la librería y un servicio, el CI instalaría la versión de `main` y probaría código desactualizado;
- el repositorio tendría que ser público, o Docker y el CI necesitarían un token.

Instalada **por ruta**, la librería y los servicios cambian en el mismo commit y el CI los prueba juntos. Instalar desde GitHub tendría sentido si la librería viviera en otro repositorio.

### Contenido

| Módulo                   | Contenido                                                                     |
|--------------------------|-------------------------------------------------------------------------------|
| `models/`                | Modelos de entrada y salida.                                                  |
| `document_validation.py` | Validación del archivo.                                                       |
| `document_reader.py`     | Lectura de `.docx` y `.xlsx`.                                                 |
| `extractor.py`           | `QuestionnaireExtractor`. Recibe un `genai.Client` ya creado, así que no depende del proveedor. |
| `exceptions.py`          | Errores con su código y estado HTTP.                                          |
| `settings.py`            | `ExtractorSettings`, la configuración común.                                  |
| `api.py`                 | `create_app` y `get_extractor`: endpoints, CORS y manejo de errores.          |

El extractor se crea **en el primer request** y no al arrancar (`get_extractor`). Así el servicio arranca, y sus tests corren, sin credenciales.

### Errores nuevos

| HTTP | `error`                   | Cuándo                                                              |
|------|---------------------------|---------------------------------------------------------------------|
| 429  | `limite_de_uso`           | El proveedor respondió 429 (cuota agotada, típico del free tier) o 402 (proyecto de pago sin crédito). |
| 502  | `error_modelo`            | El proveedor respondió con otro error.                              |
| 503  | `servicio_no_configurado` | `extractor-gemini` no tiene `GEMINI_API_KEY`.                       |

Antes, un error del proveedor terminaba en un 500 sin explicación. Ahora los dos extractores devuelven un `ErrorResponse` claro. En `extract-sheets`, el error de una hoja, por ejemplo un 429, no afecta a las demás.

## Docker

Las imágenes de los extractores se construyen **desde la raíz del repo**, para poder copiar la librería:

```bash
docker build -t extractor-gemini -f extractor-gemini/Dockerfile .
```

```dockerfile
COPY libs/questionnaire-core /opt/questionnaire-core
COPY extractor-gemini/requirements.txt .
RUN pip install --no-cache-dir /opt/questionnaire-core -r requirements.txt
COPY extractor-gemini/app ./app
```

El `.dockerignore` de la raíz funciona como **lista de permitidos**: solo entran `libs/questionnaire-core/`, `extractor-vertex/` y `extractor-gemini/`, sin tests, entornos virtuales, `.http` ni README. Así es imposible que un `.env` u otro archivo local termine dentro de una imagen. El frontend sigue con su propio contexto (`frontend/`).

## Docker Compose

| Servicio           | Puerto | Credenciales                          |
|--------------------|--------|---------------------------------------|
| `extractor-vertex` | 8080   | ADC montado (ver doc 4)               |
| `extractor-gemini` | 7070   | `GEMINI_API_KEY` desde `.env`         |
| `frontend`         | 3000   |                                       |

En **modo desarrollo**, además del código del servicio se monta el código de la librería en `/app/questionnaire_core`. Como `uvicorn` agrega `/app` al inicio del `sys.path`, esa copia tiene prioridad sobre la instalada, y los cambios en la librería también recargan el servicio.

## CI/CD

- **Tests:** un job `test-python` con una matriz: `libs/questionnaire-core`, `extractor-vertex` y `extractor-gemini`. Cada uno instala la librería desde el mismo commit (`pip install -e "libs/questionnaire-core[dev]"`).
- **Deploy:** la matriz suma `extractor-gemini` (puerto 7070) y un `context` por servicio. Los extractores usan la raíz y el frontend, `frontend`.

## Entorno local de desarrollo

Hay un único entorno virtual en la **raíz del repo**, con la librería en modo editable:

```bash
python3 -m venv .venv
.venv/bin/pip install -e "libs/questionnaire-core[dev]" -r extractor-vertex/requirements.txt -r extractor-gemini/requirements.txt
```

En VS Code hay que seleccionar `./.venv/bin/python` como intérprete. El `extractor-vertex/.venv` anterior ya no se usa.

## Free tier de la Gemini API

- **Se asigna por proyecto.** La API key debe crearse en un proyecto **sin facturación**. Si se crea en un proyecto con facturación activa, el uso pasa al plan de pago.

  Así ocurrió en la primera prueba: la clave pertenecía a un proyecto con prepago y sin créditos, y la API respondió `402 RESOURCE_EXHAUSTED` (*"Your prepayment credits are depleted"*). La solución fue crear la clave en un proyecto nuevo de AI Studio sin facturación.
- **Los límites son bajos.** Según reportes de usuarios, `gemini-3.8-flash` permite unas pocas decenas de peticiones por día; los límites exactos se ven en AI Studio. Al agotarlos, la API responde `429 limite_de_uso`. `extract-sheets` hace una llamada por hoja, así que consume la cuota más rápido.
- **Uso de datos.** En el free tier, Google puede usar el contenido enviado para mejorar sus productos. Los cuestionarios de `examples/` son inventados.

## Configuración en GCP

Todos los comandos se ejecutan con la configuración del proyecto cargada (`source .env.gcp`).

### 1. API key de AI Studio

1. Entrar a https://aistudio.google.com/apikey con la cuenta personal.
2. **Create API key**, en un proyecto **sin facturación**. AI Studio ofrece crear uno nuevo.
3. Copiar la clave. En local va en `.env` (`GEMINI_API_KEY=...`), que no se sube al repositorio.

### 2. Secret Manager y service account

```bash
# Habilitar Secret Manager
gcloud services enable secretmanager.googleapis.com

# Guardar la API key como secreto (se lee de la terminal, no queda en el historial de comandos)
read -s -p "API key: " GEMINI_API_KEY && printf '%s' "$GEMINI_API_KEY" | \
  gcloud secrets create gemini-api-key --data-file=- && unset GEMINI_API_KEY

# Service account propia para extractor-gemini, con acceso solo a ese secreto
gcloud iam service-accounts create extractor-gemini-runtime \
  --display-name="extractor-gemini en Cloud Run"

SA_GEMINI=extractor-gemini-runtime@$GCP_PROJECT_ID.iam.gserviceaccount.com

gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:$SA_GEMINI" --role=roles/secretmanager.secretAccessor
```

El permiso se da **sobre el secreto**, no sobre el proyecto: la service account solo puede leer `gemini-api-key`. No necesita permisos de Vertex AI.

Si la clave ya está en el `.env` local, se puede enviar desde ahí, sin escribirla. Hay que hacerlo **desde la raíz del repo** y comprobar antes que se leyó:

```bash
K=$(grep '^GEMINI_API_KEY=' .env | cut -d= -f2- | tr -d '\n'); echo "longitud: ${#K}"   # debe ser mayor que 0
printf '%s' "$K" | gcloud secrets versions add gemini-api-key --data-file=- ; unset K
gcloud secrets versions list gemini-api-key   # debe aparecer la versión 1, ENABLED
```

**Problema encontrado:** el primer despliegue falló con *"Secret .../gemini-api-key/versions/latest was not found"*. El secreto existía, pero **sin ninguna versión**: se creó con `--data-file=-` desde una terminal que no estaba en la raíz del repo, el `grep` no encontró el `.env` y `gcloud` recibió un contenido vacío. La solución fue agregar la clave como versión (`gcloud secrets versions add`) y repetir el despliegue. Por eso se comprueba la longitud antes de enviarla.

### 3. Primer despliegue manual

El pipeline actualiza servicios que ya existen. El primero se crea a mano, para dejar configurados el secreto, la service account, el CORS y el acceso público:

```bash
docker build -t $REG/extractor-gemini:v1 -f extractor-gemini/Dockerfile .
docker push $REG/extractor-gemini:v1

FRONTEND_URLS="https://frontend-yu7lpen3ba-uc.a.run.app,https://frontend-$GCP_PROJECT_NUMBER.us-central1.run.app"

gcloud run deploy extractor-gemini \
  --image=$REG/extractor-gemini:v1 \
  --region=us-central1 \
  --port=7070 \
  --service-account=$SA_GEMINI \
  --set-secrets=GEMINI_API_KEY=gemini-api-key:latest \
  --update-env-vars="^@^CORS_ORIGINS=$FRONTEND_URLS" \
  --allow-unauthenticated \
  --min-instances=0 --max-instances=2
```

- `--set-secrets` expone el secreto como la variable `GEMINI_API_KEY`. La clave nunca aparece en la configuración visible del servicio.
- `github-deployer` ya puede desplegar con `extractor-gemini-runtime`, porque tiene `roles/iam.serviceAccountUser` en el proyecto. Los despliegues siguientes del pipeline conservan el secreto, la service account y las variables.

### 4. Verificar

```bash
URL=https://extractor-gemini-$GCP_PROJECT_NUMBER.us-central1.run.app
curl $URL/health
curl -F "file=@examples/01-tipo-doc/cuestionario.docx" $URL/v1/questionnaires/extract
```

### Cambiar la API key

```bash
read -s -p "API key: " GEMINI_API_KEY && printf '%s' "$GEMINI_API_KEY" | \
  gcloud secrets versions add gemini-api-key --data-file=- && unset GEMINI_API_KEY
gcloud run services update extractor-gemini --region=us-central1 --set-secrets=GEMINI_API_KEY=gemini-api-key:latest
```

El `update` crea una revisión nueva que lee la última versión del secreto.

## Tests

| Paquete                  | Tests | Qué prueban                                                     |
|--------------------------|-------|-----------------------------------------------------------------|
| `libs/questionnaire-core`| 66    | Toda la lógica: modelos, validación, lectores, extractor, `extract-sheets`, API, CORS y los errores 429/502 del proveedor. |
| `extractor-vertex`       | 2     | Crea el cliente con `vertexai=True`, el proyecto y la ubicación. |
| `extractor-gemini`       | 4     | Crea el cliente con la API key; sin API key responde `503 servicio_no_configurado`. |

Todos corren sin credenciales. Después de la refactorización se verificó `extractor-vertex` con una llamada real a Vertex AI con el caso `01-tipo-doc`: HTTP 200, idioma `es` y 3 ítems.

## Comparación con Vertex AI

Se probó `extractor-gemini` en local, contra la Gemini API real, con los tres casos de `examples/`. Cada resultado se guardó como `resultado-gemini.json`, junto al de Vertex AI (`resultado.json`).

| Caso           | HTTP | Tiempo | Ítems | ¿Igual a Vertex AI?                                     |
|----------------|------|--------|-------|---------------------------------------------------------|
| `01-tipo-doc`  | 200  | ~6 s   | 3     | Sí: tipos, alternativas, respuestas, idioma y enunciados |
| `02-tipo-xlsx` | 200  | ~17 s  | 10    | Sí                                                      |
| `03-tipo-pdf`  | 200  | ~18 s  | 12    | Sí                                                      |

Con el mismo modelo (`gemini-3.8-flash`), el mismo prompt y `temperature=0` / `seed=0`, los dos proveedores dan exactamente el mismo resultado. Era lo esperado: los dos ejecutan el mismo modelo y la librería compartida garantiza que la configuración sea idéntica. La elección entre ellos depende del costo y de los límites de uso, no de la calidad de la extracción.

## Despliegue en Cloud Run

Verificado después del primer despliegue:

| Comprobación                         | Resultado                                          |
|--------------------------------------|----------------------------------------------------|
| `GET /health`                        | `{"status":"ok"}`                                  |
| `POST /v1/questionnaires/extract` con `01-tipo-doc` | HTTP 200 en unos 7 s, idioma `es`, 3 ítems |
| CORS                                 | Permite el frontend de Cloud Run                   |
| Service account y puerto             | `extractor-gemini-runtime`, 7070                   |

## Pendiente

- Que el frontend permita elegir el extractor.
