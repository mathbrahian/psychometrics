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
