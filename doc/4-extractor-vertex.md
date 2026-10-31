# 4 - Extractor Vertex

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

## Decisión general: una sola llamada al modelo

Cada documento se procesa con **una sola llamada a Vertex AI**, con todo el contenido. No se divide el documento en partes para procesarlas por separado.

- Un cuestionario, incluso de cientos de ítems, cabe de sobra en el contexto de entrada de Gemini.
- Evita unir resultados parciales, renumerar ítems o resolver duplicados entre partes.
- Para que sea robusto se controla el tamaño máximo del archivo, el límite de tokens de salida y las respuestas cortadas por llegar a ese límite.

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

## Parte 1: modelos de entrada y salida

Los modelos se definen con Pydantic en `extractor-vertex/app/models/`. Sirven para validar los datos y para documentar la API en `/docs`. Más adelante, el mismo modelo de salida se usará como esquema de la respuesta estructurada de Gemini, así que el esquema se define una sola vez.

**Idioma del código:** el código funcional (clases, campos, funciones y tests) está en inglés; la documentación, los comentarios y las salidas JSON, en español. El JSON usa los nombres que exige la prueba (`titulo`, `enunciado`...) gracias a los **alias** de Pydantic:

```python
statement: str = Field(alias="enunciado", ...)
```

Con `validate_by_name`, `validate_by_alias` y `serialize_by_alias`, los modelos aceptan ambos nombres al validar y siempre serializan con el nombre en español. Por eso se fija `pydantic==2.14.2` en `requirements.txt`, ya que esas opciones requieren Pydantic 2.11 o superior.

### Entrada (`input_schemas.py`)

| Modelo             | Descripción                                                                 |
|--------------------|-----------------------------------------------------------------------------|
| `DocumentFormat`   | Enum con los formatos soportados: `pdf`, `docx`, `xlsx`.                    |
| `MIME_TYPES`       | Tipo MIME esperado para cada formato, para validar el contenido real del archivo. |
| `InputDocument`    | Documento recibido ya leído en memoria: `filename`, `format`, `content` y la propiedad `size_bytes`. |

El archivo llega a la API como `multipart/form-data`. `InputDocument` es la representación interna una vez leído y validado, y es lo que reciben las capas siguientes.

### Salida (`output_schemas.py`)

Campo en el código → nombre en el JSON:

```
Questionnaire
├── title           → titulo: str | None
├── language        → idioma: str            (ISO 639-1)
├── total_items     → total_items: int       (≥ 0)
└── items           → items: list[Item]
    ├── number          → numero: int        (≥ 1)
    ├── statement       → enunciado: str
    ├── type            → tipo: ItemType
    ├── options         → alternativas: list[Option]
    │   ├── value           → valor: int | str
    │   └── text            → texto: str
    └── correct_answer  → respuesta_correcta: int | str | None
```

| Modelo          | Descripción                                                                 |
|-----------------|-----------------------------------------------------------------------------|
| `ItemType`      | Enum. Miembros en inglés (`LIKERT_SCALE`, `MULTIPLE_CHOICE`, `TRUE_FALSE`, `OPEN_ENDED`, `MATCHING`), valores en español: `escala_likert`, `seleccion_multiple`, `verdadero_falso`, `desarrollo`, `emparejamiento`. |
| `Option`        | Una alternativa de respuesta.                                               |
| `Item`          | Una pregunta o afirmación del cuestionario.                                 |
| `Questionnaire` | El resultado completo de la extracción.                                     |
| `ErrorResponse` | Respuesta de error: `error` (código, por ejemplo `formato_invalido`) y `detalle` (mensaje para el usuario). |

Cada campo lleva una `description`. Además de documentar la API, servirá de guía para el modelo cuando se use como esquema de respuesta.

### Supuestos

- **`valor` acepta número o texto:** las escalas Likert usan números (0, 1, 2...) y la selección múltiple usa letras (A, B, C...), como en el ejemplo de la prueba.
- **`respuesta_correcta` acepta número, texto o `null`:** es `null` cuando el documento no la indica o cuando el tipo de ítem no tiene una respuesta correcta, como en Likert o desarrollo.
- **`titulo` puede ser `null`:** no todos los documentos tienen título, y es preferible a inventarlo.
- **`idioma` es cualquier código ISO 639-1 de dos letras:** la prueba exige al menos italiano, español e inglés, pero no se restringe a esos tres para no fallar con otros idiomas.
- **`alternativas` es una lista vacía por defecto**, que es el caso de los ítems de desarrollo.

La representación de los ítems de `emparejamiento`, que el ejemplo de la prueba no muestra, se define en la parte 4.

### Tests (`tests/test_schemas.py`)

- El JSON de ejemplo del enunciado (`tests/data/spec_example.json`) es válido y, al serializarlo, se obtiene exactamente el mismo JSON, con los nombres en español.
- Los modelos también aceptan los nombres en inglés y los serializan en español.
- Un ítem de desarrollo no tiene alternativas por defecto.
- Se rechazan un tipo de ítem desconocido, un número de ítem menor a 1, un idioma que no sea ISO 639-1 y un formato de documento no soportado.

## Parte 2: extractor con Vertex AI

`app/questionnaire_extractor.py` contiene la clase `QuestionnaireExtractor`, que envía el documento a Gemini en Vertex AI y devuelve un `Questionnaire` validado.

### SDK y modelo

- **SDK:** `google-genai` (`genai.Client(vertexai=True)`), el SDK actual de Google. El antiguo `vertexai.generative_models` está obsoleto.
- **Modelo:** `gemini-3.8-flash`, configurable con `GENAI_MODEL`. Se elige Flash por su equilibrio entre precio y calidad para salida estructurada.
- **Ubicación:** `global`, porque los modelos Gemini 3.x se sirven desde el endpoint global de Vertex AI. Cloud Run sigue en `us-central1`.
- **Llamada asíncrona** (`client.aio`): mientras espera a Vertex AI, la instancia de Cloud Run puede atender otras peticiones.
- El cliente se crea **una sola vez** al instanciar el extractor, no en cada petición.

### Salida estructurada

La configuración de la llamada fuerza al modelo a responder con el esquema de la parte 1:

```python
response_mime_type="application/json",
response_json_schema=Questionnaire.model_json_schema(),
```

El esquema se genera del mismo modelo de Pydantic que usa la API, con los nombres en español y las `description` de cada campo, que le sirven de guía al modelo. Así el esquema se define una sola vez.

### Instrucciones del sistema

`SYSTEM_INSTRUCTION` define las reglas de extracción:

- **Generales:** mantener el orden del documento, numerar desde 1, no inventar ítems y no tratar como ítems las instrucciones o los títulos de sección.
- **Por tipo de ítem:**
  - Likert con valores numéricos desde 0;
  - selección múltiple con letras;
  - verdadero/falso con `V` y `F`;
  - desarrollo sin alternativas;
  - emparejamiento como un solo ítem (ver parte 4).
- **Respuesta correcta:** solo si el documento la indica. El modelo nunca debe resolver los ítems por su cuenta.


### Parámetros del modelo

Se configuran con variables de entorno (`app/config.py`, con `pydantic-settings`), así se ajustan sin tocar código:

| Variable                | Default            | Motivo                                                        |
|-------------------------|--------------------|---------------------------------------------------------------|
| `GENAI_MODEL`           | `gemini-3.8-flash` | Modelo de Gemini.                                             |
| `GOOGLE_CLOUD_LOCATION` | `global`           | Endpoint de Vertex AI.                                        |
| `MAX_OUTPUT_TOKENS`     | `32768`            | Margen para el JSON de cuestionarios largos.                  |
| `TEMPERATURE`           | `0.0`              | Respuestas deterministas: el mismo documento da el mismo resultado. |
| `TOP_P`                 | `0.95`             |                                                               |
| `SEED`                  | `0`                | Reproducibilidad, junto con la temperatura en 0.              |

### Filtros de seguridad

Los `safety_settings` se desactivan (`OFF`). Los cuestionarios psicológicos tratan temas sensibles, como ansiedad, autolesiones o pensamientos negativos, y los filtros podrían bloquear la respuesta de un cuestionario legítimo.

### Errores

Las excepciones están en `app/exceptions.py`. Cada una tiene un `code`, que será el campo `error` de la respuesta de la API:

| Excepción                    | `code`                       | Cuándo                                                   |
|------------------------------|------------------------------|----------------------------------------------------------|
| `UnsupportedFormatError`     | `formato_invalido`           | Formato no soportado.                                    |
| `TruncatedResponseError`     | `documento_demasiado_grande` | El modelo llegó a `MAX_OUTPUT_TOKENS` y el JSON quedó cortado (`finish_reason = MAX_TOKENS`). |
| `InvalidModelResponseError`  | `respuesta_invalida`         | Respuesta vacía, bloqueada o que no cumple el esquema.   |
| `NoItemsFoundError`          | `sin_items`                  | El documento no tiene ítems.                             |

Se valida la respuesta en lugar de confiar en el modelo: aunque se le pida un esquema, la salida se vuelve a validar con Pydantic.

### Formatos

- **PDF:** se envía directamente al modelo (`Part.from_bytes`). Gemini lee el PDF completo, incluido su diseño, y también los PDF escaneados.
- **`.docx`:** Gemini no lo lee directamente, así que se convierte a texto (ver parte 3).
- **`.xlsx`:** se convierte a texto (ver parte 4).

### Tests (`tests/test_questionnaire_extractor.py`)

Vertex AI se simula con un cliente falso, así que los tests no tienen costo ni dependen de la red:

- Una respuesta válida del modelo se convierte en el `Questionnaire` esperado.
- Se hace **una sola llamada**, con el PDF como contenido.
- La configuración pide JSON con el esquema de `Questionnaire` y los filtros de seguridad desactivados.
- Se lanza el error correcto cuando la respuesta está cortada, vacía, no cumple el esquema o no tiene ítems.
- Un `.docx` se rechaza sin llamar al modelo.

Los tests asíncronos usan `pytest-asyncio`, en modo `auto` (`pytest.ini`).

## Parte 3: endpoint y validación de entrada

### Endpoint

```
POST /v1/questionnaires/extract
Content-Type: multipart/form-data
file: <archivo>
```

Devuelve el `Questionnaire` en JSON, con los nombres en español. La ruta está versionada (`/v1`) para poder cambiar el contrato sin romper a quien ya consume la API.

El extractor se inyecta con `Depends(get_extractor)`:

- En producción se crea **una sola instancia por proceso** (`lru_cache`), junto con su cliente de Vertex AI.
- En los tests se reemplaza por uno falso con `app.dependency_overrides`.

### Validación del archivo (`app/document_validation.py`)

Antes de llamar al modelo, el archivo se valida en este orden:

1. **Extensión:** debe ser `.pdf`, `.docx` o `.xlsx`. El `.doc` antiguo, que es un formato binario distinto, se rechaza.
2. **No vacío.**
3. **Tamaño máximo:** `MAX_FILE_SIZE_MB`, 10 MB por defecto. Pone un techo al costo y al riesgo de respuestas cortadas.
4. **Contenido real:** los primeros bytes deben coincidir con la extensión. Un PDF empieza con `%PDF`; `.docx` y `.xlsx` son archivos ZIP (`PK`). Así se detecta, por ejemplo, un `.docx` renombrado a `.pdf`. No se confía en el `Content-Type` que envía el cliente.

Si algo falla, el modelo no se llama, así que un archivo inválido no tiene costo.

### Lectura de `.docx` (`app/document_reader.py`)

Con `python-docx` se extraen los párrafos y las tablas **en el orden del documento**. Las filas de las tablas se unen con ` | `. El texto resultante se envía al modelo como `Part.from_text`.

### Errores

Un `exception_handler` convierte cualquier `ExtractionError` en un `ErrorResponse` con el código HTTP de la excepción:

| HTTP | `error`                      | Cuándo                                              |
|------|------------------------------|-----------------------------------------------------|
| 400  | `archivo_vacio`              | El archivo no tiene contenido.                      |
| 413  | `archivo_demasiado_grande`   | Supera `MAX_FILE_SIZE_MB`.                          |
| 415  | `formato_invalido`           | Extensión no soportada o contenido que no coincide. |
| 422  | `sin_items`                  | No se detectaron ítems.                             |
| 422  | `documento_demasiado_grande` | La respuesta del modelo quedó cortada.              |
| 502  | `respuesta_invalida`         | El modelo respondió vacío o fuera del esquema.      |

```json
{ "error": "formato_invalido", "detalle": "El formato '.doc' no está soportado. Formatos válidos: .pdf, .docx, .xlsx." }
```

### Casos de prueba (`examples/`)

Cada caso vive en su carpeta, con el cuestionario de entrada y el `resultado.json` que devolvió el extractor con Vertex AI real. Es la carpeta `/examples` que pide la prueba, y los tests la usan como datos.

| Caso                  | Entrada | Resultado |
|-----------------------|---------|-----------|
| `01-tipo-doc` | `.docx` | 3 ítems correctos: Likert con valores 0 a 3, selección múltiple con respuesta correcta `C` y desarrollo sin alternativas. |
| `02-tipo-xlsx` | `.xlsx` | Ver parte 4. |

Primera llamada real: HTTP 200 en unos 12 segundos. Gemini aceptó sin cambios el esquema generado por Pydantic, que incluye `$defs` y `anyOf`.

### Tests

- `test_document_validation.py`: extensiones válidas e inválidas, archivo vacío, tamaño máximo y contenido que no coincide con la extensión.
- `test_document_reader.py`: el texto del `.docx` de ejemplo sale completo y en orden.
- `test_api.py`, con el extractor simulado:
  - respuesta 200 con los nombres en español;
  - el documento validado llega al extractor;
  - cada error devuelve su código HTTP y su `error`;
  - con un archivo inválido no se llama al extractor.
- `test_schemas.py`: cada `examples/*/resultado.json` cumple el esquema.

Los datos de prueba compartidos (`EXAMPLES_DIR`, `DATA_DIR`) y la configuración de entorno de los tests están en `tests/conftest.py`.

## Parte 4: Excel y emparejamiento

### Lectura de `.xlsx` (`app/document_reader.py`)

Con `openpyxl` se lee cada hoja fila por fila. Cada fila es una línea, sus celdas se separan con ` | `, y se omiten las filas vacías y las celdas vacías al final de cada fila. Se leen los valores calculados de las celdas, no sus fórmulas. Igual que el `.docx`, el texto se envía al modelo como `Part.from_text`.

En `/extract`, de un Excel **solo se lee la primera hoja**, porque ese endpoint devuelve un cuestionario por archivo. Las demás hojas pueden tener otros cuestionarios, instrucciones o resultados esperados que no deben llegar al modelo.

### Regla de emparejamiento

El primer criterio separaba cada elemento de la columna izquierda en un ítem distinto. Con el caso `02-tipo-xlsx` se vieron dos problemas:

- El documento numera el emparejamiento como **un solo ítem**. Separarlo cambiaba `total_items` (12 en lugar de 10) y la numeración.
- Se perdía el enunciado real: los ítems quedaban como `"Italia"` y desaparecía la instrucción *"Relacione cada país con su capital"*.

Regla final, en `SYSTEM_INSTRUCTION`:

- El conjunto de elementos a relacionar es **un solo ítem**, con la instrucción como `enunciado`.
- `alternativas` incluye primero la columna izquierda, con `valor` numérico (1, 2, 3...), y después la derecha, con `valor` en letras minúsculas (a, b, c...).
- `respuesta_correcta`, si el documento la indica, es un texto con los pares: `"1-b; 2-c; 3-a"`.

```json
{
  "numero": 10,
  "enunciado": "Relacione cada país con su capital.",
  "tipo": "emparejamiento",
  "alternativas": [
    { "valor": 1, "texto": "Italia" }, { "valor": 2, "texto": "Francia" }, { "valor": 3, "texto": "España" },
    { "valor": "a", "texto": "Madrid" }, { "valor": "b", "texto": "Roma" }, { "valor": "c", "texto": "París" }
  ],
  "respuesta_correcta": "1-b; 2-c; 3-a"
}
```

**Likert:** se mantiene la regla de empezar en 0, salvo que el documento indique otros valores. Una escala de 5 puntos sin valores indicados queda de 0 a 4, coherente con el ejemplo de la prueba, que usa 0 a 3.

### Endpoint especializado: `POST /v1/questionnaires/extract-sheets`

Un plus sobre lo que pide la prueba: procesa **todas las hojas** de un Excel, cada una como un cuestionario independiente.

**Se hizo un endpoint nuevo en lugar de cambiar `/extract`**, por estas razones:

- `/extract` cumple el contrato de la prueba: siempre devuelve **un** cuestionario. Si a veces devolviera un objeto y a veces una lista, quien lo consume tendría que adivinar la forma de la respuesta.
- Cada endpoint tiene un tipo de respuesta fijo, bien documentado en `/docs` y fácil de testear.

**Funcionamiento:**

- **Solo acepta `.xlsx`.** Otro formato devuelve `415 formato_invalido`.
- **Paralelo:** cada hoja con contenido se envía a Vertex AI en su propia llamada, todas al mismo tiempo con `asyncio.gather`. Un Excel de 3 hojas tarda prácticamente lo mismo que uno de una hoja. No contradice la decisión de una sola llamada por documento, porque no se parte un cuestionario: cada hoja **es** un cuestionario completo.
- **Errores aislados:** el error de una hoja no afecta a las demás. Cada resultado trae el cuestionario o el error de esa hoja.
- **Las hojas vacías se omiten** sin llamar al modelo. Si todas están vacías, devuelve `422 sin_items`.
- **Límite de hojas:** `MAX_SHEETS`, 10 por defecto. Cada hoja es una llamada con costo, así que un Excel con más hojas con contenido devuelve `413 demasiadas_hojas` sin llamar al modelo.

**Respuesta**, una lista de `SheetResult`:

```json
[
  { "hoja": "Cuestionario_ES", "cuestionario": { "titulo": "...", "idioma": "es", "total_items": 10, "items": [...] }, "error": null },
  { "hoja": "Cuestionario_IT", "cuestionario": { "titulo": "...", "idioma": "it", "total_items": 10, "items": [...] }, "error": null },
  { "hoja": "Hoja rota",       "cuestionario": null, "error": { "error": "respuesta_invalida", "detalle": "..." } }
]
```

En el código, `extract` y `extract_sheets` comparten `_extract_part`, que hace la llamada al modelo y valida la respuesta, así que las reglas son las mismas en los dos endpoints.

### Caso de prueba `02-tipo-xlsx`

El mismo cuestionario de 10 ítems en tres hojas (español, italiano e inglés), con los 5 tipos de ítem.

| Archivo               | Endpoint          | Resultado con Vertex AI real                                         |
|-----------------------|-------------------|----------------------------------------------------------------------|
| `resultado.json`      | `/extract`        | Primera hoja: 10 ítems, idioma `es`, HTTP 200 en unos 18 s.          |
| `resultado-hojas.json`| `/extract-sheets` | Las 3 hojas, idiomas `es`, `it` y `en`, 10 ítems cada una, HTTP 200 en unos 19 s. |

En las tres hojas salieron correctas las respuestas de selección múltiple, verdadero/falso y emparejamiento (`"1-b; 2-c; 3-a"`).

### Tests

- `test_document_reader.py`: de un Excel, `/extract` solo lee la primera hoja y se omiten las celdas vacías al final de cada fila.
- `test_extract_sheets.py`:
  - se leen todas las hojas del ejemplo y cada una va en su propia llamada;
  - el error de una hoja no afecta a las demás;
  - las hojas vacías se omiten;
  - un Excel sin contenido o con demasiadas hojas se rechaza sin llamar al modelo;
  - el endpoint devuelve la lista con los nombres en español y rechaza archivos que no son `.xlsx`.

  Los Excel de prueba se crean en memoria con `openpyxl`.
- `test_schemas.py`: también valida cada `examples/*/resultado-hojas.json`.

## Despliegue en Cloud Run

El pipeline despliega solo al mergear a `main`. Un push a la rama solo corre los tests en el PR. Antes de mergear se verificó que la nube esté lista:

| Qué                                   | Estado esperado                                        |
|---------------------------------------|--------------------------------------------------------|
| API de Vertex AI                      | `aiplatform.googleapis.com` habilitada                 |
| Service account de `extractor-vertex` | `extractor-vertex-runtime`, solo con `roles/aiplatform.user` |
| `GOOGLE_CLOUD_PROJECT`                | Proyecto de GCP                                        |
| `GOOGLE_CLOUD_LOCATION`               | `global`                                               |
| `CORS_ORIGINS`                        | Las dos URLs del frontend                              |
| Tests                                 | Pasan en un entorno virtual limpio, igual que en el CI |

**Problema encontrado:** `GOOGLE_CLOUD_LOCATION` estaba en `us-central1`, porque se configuró con una versión anterior de este documento. En local funcionaba porque el compose usa `global`. En Cloud Run, Vertex AI podría responder que el modelo no existe en esa región. Se corrige sin redesplegar:

```bash
gcloud run services update extractor-vertex --update-env-vars=GOOGLE_CLOUD_LOCATION=global
```

**Problema en el CI:** al mergear el PR, el pipeline falló en `test_requires_file`. Ese test no reemplazaba el extractor por el falso, así que FastAPI creaba el cliente real de Vertex AI, que busca credenciales al construirse. En GitHub Actions no hay credenciales, y por eso fallaba. En local pasaba porque el SDK encontraba las credenciales por defecto de la máquina, aunque no llegaba a hacer ninguna llamada.

**Solución:** ese test también usa el extractor falso. Para detectar este tipo de dependencia, los tests se verifican sin ninguna credencial disponible:

```bash
env -u GOOGLE_APPLICATION_CREDENTIALS CLOUDSDK_CONFIG=/nonexistent HOME=/tmp pytest -q
```

Como los tests fallaron, el job `deploy` no se ejecutó y Cloud Run siguió con la versión anterior.

Para revisar las variables y la service account del servicio:

```bash
gcloud run services describe extractor-vertex \
  --format="value(spec.template.spec.serviceAccountName, spec.template.spec.containers[0].env)"
```

Prueba después del merge:

```bash
curl -F "file=@examples/01-tipo-doc/cuestionario.docx" \
  https://extractor-vertex-<PROJECT_NUMBER>.us-central1.run.app/v1/questionnaires/extract
```

## Resultado esperado

Desde el frontend, o directamente contra la API, se sube un cuestionario y se recibe el JSON estructurado, tanto en local con Docker Compose como en Cloud Run.
