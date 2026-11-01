# Videos de avance

Registro en video de cada etapa del proyecto, en el mismo orden que los documentos de `doc/`.

| # | Video | Documentación relacionada | Contenido |
|---|-------|---------------------------|-----------|
| 1 | [Ver video](https://youtu.be/JHTu_3EpiO4) | [1 - Lectura y planeación](1-lectura-y-planeacion.md), [2 - Aplicación nativa](2-aplicacion-nativa.md) | Lectura de la prueba, planeación y preparación del entorno nativo de nube |
| 2 | [Ver video](https://youtu.be/sdRRXk8aNe4) | [2 - Aplicación nativa](2-aplicacion-nativa.md) | Despliegue en Cloud Run y pipeline de CI/CD desde GitHub con Workload Identity Federation |
| 3 | [Ver video](https://youtu.be/eZNttZoc7JQ) | [4 - Extractor Vertex](4-extractor-vertex.md) | Microservicio de extracción con Gemini en Vertex AI: credenciales locales y en Cloud Run, modelos de entrada y salida, extractor, endpoint y casos de prueba |
| 4 | [Ver video](https://youtu.be/JrWypm4buGY) | [4 - Extractor Vertex](4-extractor-vertex.md) | Cierre del extractor con Vertex AI: lectura de Excel, endpoint `extract-sheets` con las hojas en paralelo, emparejamiento como un solo ítem y caso de prueba en PDF |
| 5 | [Ver video](https://youtu.be/Xh-uiG-vrBg) | [11 - Frontend essentials](11-frontend-essentials.md) | Primer paso del frontend: subir el archivo al extractor y mostrar la respuesta en crudo, y el frontend en el puerto 3000 en todos los entornos |
| 6 | [Ver video](https://youtu.be/qP7xNOG01CU) | [14 - Extractor Gemini](14-extractor-gemini.md) | Librería compartida `questionnaire-core` y `extractor-gemini` con la Gemini API: Secret Manager, despliegue en Cloud Run y comparación con Vertex AI |
| 7 | [Ver video](https://youtu.be/XE60ctTc6mQ) | [16 - Backend](16-backend.md) | Backend con inicio de sesión de un solo usuario (JWT y argon2), consumo de los dos extractores con token de identidad de Google, extractores cerrados al público y frontend que inicia sesión y extrae a través del backend |
| 8 | [Ver video](https://youtu.be/SLykm3qkLLs) | [16 - Backend](16-backend.md) | Base de datos en Cloud SQL con PostgreSQL: creación de la instancia más barata, conexión desde Cloud Run, capas de DDD, migraciones con Alembic y endpoints para guardar, listar y eliminar cuestionarios |
| 9 | [Ver video](https://youtu.be/HHIYMdQgaWQ) | [16 - Backend](16-backend.md) (paso 6) | Frontend plano: inicio de sesión, extracción con Gemini API o Vertex AI, cuestionario en pantalla, descarga del JSON, guardado, lista, eliminación y limpieza de la consulta |
| 10 | [Ver video](https://www.youtube.com/watch?v=7phXoXy2F5g) | [16 - Backend](16-backend.md) (paso 6) | Evolución del frontend solo con CSS: tipografía Poppins y paleta violeta, indicadores de carga, mensajes de error y confirmación visibles, y modal para ver los cuestionarios guardados |
