# 4 - Extractor Vertex: reglas de negocio

Este documento recoge la lógica del extractor: qué recibe, qué devuelve y las reglas que debe cumplir el resultado. Se construye por partes, y cada parte se sube y documenta por separado.

## Decisión general: una sola llamada al modelo

Cada documento se procesa con **una sola llamada a Vertex AI**, con todo el contenido. No se divide el documento en partes para procesarlas por separado.

- Un cuestionario, incluso de cientos de ítems, cabe de sobra en el contexto de entrada de Gemini.
- Evita unir resultados parciales, renumerar ítems o resolver duplicados entre partes.
- Para que sea robusto se controla el tamaño máximo del archivo, el límite de tokens de salida y las respuestas cortadas por llegar a ese límite.

## Parte 1: modelos de entrada y salida

Los modelos se definen con Pydantic en `extractor-vertex/app/models/`. Sirven para validar los datos y para documentar la API en `/docs`. Más adelante, el mismo modelo de salida se usará como esquema de la respuesta estructurada de Gemini, así que el esquema se define una sola vez.

Los nombres de clases y campos están en español para coincidir con el JSON que pide la prueba.

### Entrada (`input_schemas.py`)

| Modelo             | Descripción                                                                 |
|--------------------|-----------------------------------------------------------------------------|
| `FormatoDocumento` | Enum con los formatos soportados: `pdf`, `docx`, `xlsx`.                    |
| `MIME_TYPES`       | Tipo MIME esperado para cada formato, para validar el contenido real del archivo. |
| `DocumentoEntrada` | Documento recibido ya leído en memoria: `nombre_archivo`, `formato`, `contenido` y la propiedad `tamano_bytes`. |

El archivo llega a la API como `multipart/form-data`. `DocumentoEntrada` es la representación interna una vez leído y validado, y es lo que reciben las capas siguientes.

### Salida (`output_schemas.py`)

```
Cuestionario
├── titulo: str | None
├── idioma: str            (ISO 639-1)
├── total_items: int       (≥ 0)
└── items: list[Item]
    ├── numero: int        (≥ 1)
    ├── enunciado: str
    ├── tipo: TipoItem
    ├── alternativas: list[Alternativa]
    │   ├── valor: int | str
    │   └── texto: str
    └── respuesta_correcta: int | str | None
```

| Modelo          | Descripción                                                                 |
|-----------------|-----------------------------------------------------------------------------|
| `TipoItem`      | Enum: `escala_likert`, `seleccion_multiple`, `verdadero_falso`, `desarrollo`, `emparejamiento`. |
| `Alternativa`   | Una opción de respuesta.                                                    |
| `Item`          | Una pregunta o afirmación del cuestionario.                                 |
| `Cuestionario`  | El resultado completo de la extracción.                                     |
| `ErrorRespuesta`| Respuesta de error: `error` (código) y `detalle` (mensaje para el usuario). |

Cada campo lleva una `description`. Además de documentar la API, servirá de guía para el modelo cuando se use como esquema de respuesta.

### Supuestos

- **`valor` acepta número o texto:** las escalas Likert usan números (0, 1, 2...) y la selección múltiple usa letras (A, B, C...), como en el ejemplo de la prueba.
- **`respuesta_correcta` acepta número, texto o `null`:** es `null` cuando el documento no la indica o cuando el tipo de ítem no tiene una respuesta correcta, como en Likert o desarrollo.
- **`titulo` puede ser `null`:** no todos los documentos tienen título, y es preferible a inventarlo.
- **`idioma` es cualquier código ISO 639-1 de dos letras:** la prueba exige al menos italiano, español e inglés, pero no se restringe a esos tres para no fallar con otros idiomas.
- **`alternativas` es una lista vacía por defecto**, que es el caso de los ítems de desarrollo.

Pendiente de definir en las reglas de negocio: cómo representar los ítems de `emparejamiento`, que el ejemplo de la prueba no muestra.

### Tests (`tests/test_schemas.py`)

- El JSON de ejemplo del enunciado (`tests/data/ejemplo_enunciado.json`) es válido y, al serializarlo, se obtiene exactamente el mismo JSON.
- Un ítem de desarrollo no tiene alternativas por defecto.
- Se rechazan un tipo de ítem desconocido, un número de ítem menor a 1, un idioma que no sea ISO 639-1 y un formato de documento no soportado.
