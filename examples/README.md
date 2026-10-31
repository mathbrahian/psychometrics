# Ejemplos

Cada carpeta es un caso de prueba con el cuestionario de entrada y el JSON que devolvieron los extractores: `resultado.json` (`extractor-vertex`, Vertex AI) y `resultado-gemini.json` (`extractor-gemini`, Gemini API). Todos los cuestionarios son inventados.

| Caso | Entrada | Qué prueba |
|------|---------|------------|
| [01-tipo-doc](01-tipo-doc/) | `.docx` | Escala Likert, selección múltiple con respuesta correcta y pregunta de desarrollo. Idioma: español (`es`). |
| [02-tipo-xlsx](02-tipo-xlsx/) | `.xlsx` con 3 hojas (ES, IT, EN) | Los 5 tipos de ítem, con respuestas correctas en selección múltiple, verdadero/falso y emparejamiento. `resultado.json` es la salida de `/extract`, que solo lee la primera hoja; `resultado-hojas.json` es la de `/extract-sheets`, con una respuesta por hoja. |
| [03-tipo-pdf](03-tipo-pdf/) | `.pdf` de 3 páginas | 12 ítems de los 5 tipos, agrupados en secciones ("Parte I", "Parte II"...). Las respuestas correctas están marcadas con `(X)` y en verde, y además hay una clave de respuestas en la última página. Incluye dos emparejamientos. |

Para reproducir un caso:

```bash
curl -F "file=@examples/01-tipo-doc/cuestionario.docx" http://localhost:8080/v1/questionnaires/extract
```
