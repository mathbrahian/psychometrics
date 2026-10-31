# 4 - Extractor Vertex: reglas de negocio

Este documento recoge la lógica del extractor: qué recibe, qué devuelve y las reglas que debe cumplir el resultado. Se construye por partes, y cada parte se sube y documenta por separado.

## Decisión general: una sola llamada al modelo

Cada documento se procesa con **una sola llamada a Vertex AI**, con todo el contenido. No se divide el documento en partes para procesarlas por separado.

- Un cuestionario, incluso de cientos de ítems, cabe de sobra en el contexto de entrada de Gemini.
- Evita unir resultados parciales, renumerar ítems o resolver duplicados entre partes.
- Para que sea robusto se controla el tamaño máximo del archivo, el límite de tokens de salida y las respuestas cortadas por llegar a ese límite.

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

Pendiente de definir en las reglas de negocio: cómo representar los ítems de `emparejamiento`, que el ejemplo de la prueba no muestra.

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
  - emparejamiento con un ítem por cada elemento de la columna izquierda y la columna derecha como alternativas.
- **Respuesta correcta:** solo si el documento la indica. El modelo nunca debe resolver los ítems por su cuenta.

Con esto queda definido el supuesto de **emparejamiento** que estaba pendiente en la parte 1.

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
- **`.docx` y `.xlsx`:** Gemini no los lee directamente. Por ahora devuelven `formato_invalido`; se convertirán a texto en la siguiente parte.

### Tests (`tests/test_questionnaire_extractor.py`)

Vertex AI se simula con un cliente falso, así que los tests no tienen costo ni dependen de la red:

- Una respuesta válida del modelo se convierte en el `Questionnaire` esperado.
- Se hace **una sola llamada**, con el PDF como contenido.
- La configuración pide JSON con el esquema de `Questionnaire` y los filtros de seguridad desactivados.
- Se lanza el error correcto cuando la respuesta está cortada, vacía, no cumple el esquema o no tiene ítems.
- Un `.docx` se rechaza sin llamar al modelo.

Los tests asíncronos usan `pytest-asyncio`, en modo `auto` (`pytest.ini`).
