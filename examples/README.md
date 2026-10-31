# Ejemplos

Cada carpeta es un caso de prueba con el cuestionario de entrada y el JSON que devolvió `extractor-vertex`. Todos los cuestionarios son inventados.

| Caso | Entrada | Qué prueba |
|------|---------|------------|
| [01-tipo-doc](01-tipo-doc/) | `.docx` | Escala Likert, selección múltiple con respuesta correcta y pregunta de desarrollo. Idioma: español (`es`). |
| [02-tipo-xlsx](02-tipo-xlsx/) | `.xlsx` con 3 hojas (ES, IT, EN) | Los 5 tipos de ítem, con respuestas correctas en selección múltiple, verdadero/falso y emparejamiento. `resultado.json` es la salida de `/extract`, que solo lee la primera hoja; `resultado-hojas.json` es la de `/extract-sheets`, con una respuesta por hoja. |

Para reproducir un caso:

```bash
curl -F "file=@examples/01-tipo-doc/cuestionario.docx" http://localhost:8080/v1/questionnaires/extract
```
