# 4 - Extractor Vertex: infraestructura

Esta etapa construye el core de la solución: un microservicio que recibe un cuestionario en PDF, Word o Excel y devuelve sus ítems en un JSON estructurado.

El foco está en tres cosas: la entrada de datos, la salida de datos y la conexión con Vertex AI.

## Alcance de esta etapa

### Entrada

- Un endpoint que recibe el archivo como `multipart/form-data`.
- Formatos soportados: `.pdf`, `.docx` y `.xlsx`.
- Validación del archivo: extensión, tipo real del contenido, tamaño máximo y que no esté vacío.
- Extracción del texto según el formato, antes de enviarlo al modelo.

### Salida

- El esquema JSON de la prueba, definido con modelos de Pydantic: `titulo`, `idioma`, `total_items` e `items`, y por cada ítem `numero`, `enunciado`, `tipo`, `alternativas` y `respuesta_correcta`.
- Tipos de ítem: `escala_likert`, `seleccion_multiple`, `verdadero_falso`, `desarrollo` y `emparejamiento`.
- Idioma detectado: al menos italiano, español e inglés.
- Respuestas de error claras para formato inválido, documento sin ítems y fallos del procesamiento.

### Conexión con Vertex AI

- Habilitar la API de Vertex AI (`aiplatform.googleapis.com`) en el proyecto.
- Dar a la identidad del servicio en Cloud Run el permiso para usar Vertex AI.
- En local, autenticarse con las credenciales de la cuenta de desarrollo, sin llaves en el repositorio.
- Pedirle al modelo una respuesta estructurada que cumpla el esquema de salida.

### Tests

- Validación del archivo de entrada.
- Esquema de salida.
- La llamada a Vertex AI se simula en los tests, para que no tengan costo ni dependan de la red.

Fuera de alcance: el backend, la base de datos y el extractor-gemini.

## Credenciales de Vertex AI: local y Cloud Run

El SDK de Google usa **Application Default Credentials (ADC)**: busca las credenciales en el entorno donde corre, así que el código es el mismo en local y en producción.

| Entorno   | De dónde salen las credenciales                                                   |
|-----------|-----------------------------------------------------------------------------------|
| Cloud Run | La service account asignada al servicio. No hay archivos ni llaves.               |
| Local     | Un archivo ADC de la cuenta de desarrollo, montado en el contenedor en solo lectura. |

### Aislar las credenciales de otras cuentas

`gcloud auth application-default login` escribe por defecto en `~/.config/gcloud/application_default_credentials.json`, sin importar la configuración de `gcloud` activa. Si en la misma máquina hay credenciales de otros proyectos, las sobrescribiría.

Para evitarlo, el ADC de este proyecto se genera en un directorio aparte con `CLOUDSDK_CONFIG`:

```
~/.config/gcloud/                          ← otras cuentas (no se toca)
~/.config/gcloud-psychometrics/            ← este proyecto
└── application_default_credentials.json
```

```bash
CLOUDSDK_CONFIG=~/.config/gcloud-psychometrics gcloud auth application-default login

# Proyecto de cuota, para que las librerías de Google no muestren avisos
CLOUDSDK_CONFIG=~/.config/gcloud-psychometrics gcloud auth application-default set-quota-project <PROJECT_ID>
```

En la página de consentimiento de Google hay que marcar todas las casillas de permisos. Si falta la de Google Cloud, el login falla con *"cloud-platform scope is required but not consented"*.

Regla: nunca ejecutar `gcloud auth application-default login` sin el prefijo `CLOUDSDK_CONFIG`. Para no depender de la memoria, se puede definir un alias local:

```bash
alias adc-psychometrics='CLOUDSDK_CONFIG=$HOME/.config/gcloud-psychometrics gcloud auth application-default login'
```

Verificación de que las credenciales de otras cuentas no cambiaron (la fecha debe seguir siendo la misma):

```bash
ls -la ~/.config/gcloud/application_default_credentials.json
```

### Configuración local

`docker compose` lee las variables de un archivo `.env` en la raíz, que no se sube al repositorio. La plantilla está en `.env.example`:

```bash
cp .env.example .env   # y completar GCP_PROJECT_ID
```

| Variable         | Uso                                                       |
|------------------|-----------------------------------------------------------|
| `GCP_PROJECT_ID` | Proyecto de GCP donde corre Vertex AI.                    |
| `GCP_REGION`     | Región de Cloud Run y Artifact Registry (`us-central1`).  |
| `GCP_VERTEX_LOCATION` | Ubicación de Vertex AI (`global`). Los modelos Gemini 3.x se sirven desde el endpoint global. |
| `GCP_ADC_PATH`   | Ruta del archivo ADC en la máquina local.                 |

El compose pasa al contenedor `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` y `GOOGLE_APPLICATION_CREDENTIALS`, y monta el archivo ADC en `/secrets/adc.json` en solo lectura. Si el archivo no existe, el compose falla en lugar de crear una carpeta vacía (`create_host_path: false`).

### Configuración en GCP

```bash
# 1. Habilitar la API de Vertex AI
gcloud services enable aiplatform.googleapis.com

# 2. Service account propia para el extractor, solo con permiso de usar Vertex AI
gcloud iam service-accounts create extractor-vertex-runtime \
  --display-name="extractor-vertex en Cloud Run"

gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:extractor-vertex-runtime@<PROJECT_ID>.iam.gserviceaccount.com" \
  --role=roles/aiplatform.user --condition=None

# 3. Asignarla al servicio (una sola vez; los despliegues siguientes la conservan)
gcloud run services update extractor-vertex \
  --service-account=extractor-vertex-runtime@<PROJECT_ID>.iam.gserviceaccount.com

# 4. Proyecto y región de Vertex AI como variables del servicio (Cloud Run no las define solo)
gcloud run services update extractor-vertex \
  --update-env-vars=GOOGLE_CLOUD_PROJECT=<PROJECT_ID>,GOOGLE_CLOUD_LOCATION=global
```

Se usa una service account propia en lugar de la de Compute por defecto, que tiene permisos de más.

En Cloud Run las credenciales son automáticas: el SDK obtiene un token de la service account desde el servidor de metadatos y lo renueva solo. `GOOGLE_APPLICATION_CREDENTIALS` **no se define** en producción; si se definiera, el SDK buscaría un archivo que no existe y fallaría.

### Resumen local vs Cloud Run

| Qué                                         | Local                                  | Cloud Run                                  |
|---------------------------------------------|----------------------------------------|--------------------------------------------|
| Credenciales                                | Archivo ADC montado en solo lectura    | Automático, con la service account del servicio |
| `GOOGLE_CLOUD_PROJECT` / `GOOGLE_CLOUD_LOCATION` | Las pasa el compose desde `.env`  | Variables guardadas una vez en el servicio |
| `GOOGLE_APPLICATION_CREDENTIALS`            | `/secrets/adc.json`                    | No se define                               |
| Permisos                                    | Los de la cuenta de desarrollo         | Solo `roles/aiplatform.user`               |

### Consideraciones

- **Costo:** en local se llama a la misma API con la misma facturación. Por eso los tests simulan a Vertex AI.
- **Permisos:** en local se usan los permisos de la cuenta de desarrollo, que es dueña del proyecto. En Cloud Run solo los de la service account. Un error de permisos aparecerá primero en producción, así que conviene desplegar temprano.

## Resultado esperado

Desde el frontend, o directamente contra la API, se sube un cuestionario y se recibe el JSON estructurado, tanto en local con Docker Compose como en Cloud Run.
