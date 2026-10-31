# questionnaire-core

Librería compartida por los extractores (`extractor-vertex` y `extractor-gemini`). Contiene toda la lógica que no depende del proveedor del modelo:

| Módulo                   | Contenido                                                                    |
|--------------------------|------------------------------------------------------------------------------|
| `models/`                | Modelos de entrada y salida (`Questionnaire`, `Item`, `SheetResult`...).     |
| `document_validation.py` | Validación del archivo: extensión, tamaño y contenido real.                  |
| `document_reader.py`     | Conversión de `.docx` y `.xlsx` a texto.                                     |
| `extractor.py`           | `QuestionnaireExtractor`: prompt, esquema de salida, llamada al modelo y validación de la respuesta. |
| `exceptions.py`          | Errores con su código y estado HTTP.                                         |
| `settings.py`            | `ExtractorSettings`: configuración común, que cada servicio extiende.        |
| `api.py`                 | `create_app`: la API de FastAPI con los endpoints, CORS y manejo de errores. |

Cada servicio solo define su configuración y cómo crear el cliente de `google-genai`:

```python
app = create_app("extractor-gemini", settings, build_extractor)
```

## Instalación

Se instala por ruta, desde el mismo monorepo:

```bash
pip install -e "libs/questionnaire-core[dev]"   # local, editable y con las dependencias de test
```

En Docker, cada extractor se construye desde la raíz del repo y la instala con `pip install /opt/questionnaire-core`.

## Tests

```bash
cd libs/questionnaire-core
pytest -v
```

Ningún test llama a un modelo real: el cliente de `google-genai` se reemplaza por uno falso.
