# 1 - Lectura y planeación

Este primer commit es de planeación: no hay código todavía. En esta rama se leyó la prueba y se definieron el alcance, la arquitectura y el orden de trabajo.

## Lectura de la prueba

Giunti Psychometrics necesita pasar a su plataforma digital los cuestionarios que hoy tiene en PDF, Word y Excel. Se pide una aplicación web que reciba uno de esos archivos y devuelva los ítems y sus alternativas en un JSON estandarizado.

Requisitos mínimos:

- Subir archivos PDF, `.docx` y `.xlsx`.
- Extraer los ítems, su tipo (Likert, selección múltiple, verdadero/falso, desarrollo, emparejamiento) y sus alternativas.
- Incluir la respuesta correcta cuando el documento la indique, y detectar el idioma (al menos italiano, español e inglés).
- Una UI para adjuntar el archivo, procesarlo y ver o descargar el resultado.
- Manejo de errores: formato inválido, ningún ítem detectado y fallos de procesamiento.
- Frontend en React o Next.js, backend en Python con FastAPI y un LLM gratuito.
- App desplegada y pública, README con instrucciones, carpeta `/examples` y tests con Pytest.

## Decisiones

- **Nube:** todo en GCP.
- **Monorepo** con una subcarpeta por servicio:

  ```
  psychometrics/
  ├── extractor-vertex/
  ├── frontend/
  ├── backend/
  ├── extractor-gemini/
  └── doc/
  ```

- **Local:** todo se levanta con Docker Compose.
- **Producción:** cada servicio corre en Cloud Run, con despliegue continuo desde GitHub. La idea es que se vea como una aplicación nativa de nube y no como un único servidor.

## Orden de trabajo

1. **extractor-vertex:** la API en FastAPI que recibe el archivo y devuelve el JSON, usando Vertex AI de Google para la extracción.
2. **frontend:** la UI para subir el archivo y ver el resultado. Con esto quedan cubiertos los requisitos mínimos.
3. **Despliegue e integración continua:** de GitHub a Cloud Run.
4. **backend (si da el tiempo):** guarda los cuestionarios procesados en una base de datos, con algo de DDD.
5. **extractor-gemini (si da el tiempo):** un segundo extractor que use directamente un LLM de Google, para comparar los dos enfoques.

## Forma de trabajo

Cada etapa se trabaja en su propia rama, y cada rama deja en `doc/` un documento con lo que se hizo, numerado en el mismo orden que las ramas.
