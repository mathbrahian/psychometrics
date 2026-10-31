# Ejemplos

Cada carpeta es un caso de prueba con el cuestionario de entrada y el JSON que devolvió `extractor-vertex`. Todos los cuestionarios son inventados.

| Caso | Entrada | Qué prueba |
|------|---------|------------|
| [01-tipo-doc](01-tipo-doc/) | `.docx` | Escala Likert, selección múltiple con respuesta correcta y pregunta de desarrollo. Idioma: español (`es`). |

Para reproducir un caso:

```bash
curl -F "file=@examples/01-tipo-doc/cuestionario.docx" http://localhost:8080/v1/questionnaires/extract
```
