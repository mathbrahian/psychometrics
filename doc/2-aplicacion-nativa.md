# 2 - Aplicación nativa

Lo ideal sería empezar ya con las reglas de negocio, pero antes prefiero dejar listo el entorno para que la aplicación sea nativa de nube. Muchas ideas que funcionan en local se encuentran con limitaciones al momento de desplegar.

Por eso el entorno debe funcionar igual en local y en la nube desde los primeros commits, y a partir de ahí se avanza con cambios pequeños.

## Alcance de esta etapa

- Un hola mundo en `extractor-vertex` (FastAPI).
- Un hola mundo en `frontend` (React).
- Dockerizar ambos servicios.
- Levantarlos juntos con Docker Compose y conectarlos de forma simple: el frontend llama al extractor y muestra la respuesta.
- Crear la cuenta y el proyecto en GCP.
- Desplegar ambos servicios en Cloud Run.
- Un pipeline en GitHub que ejecute los tests y despliegue en Cloud Run.
- Tests básicos con Pytest para el extractor.

Fuera de alcance: la extracción de cuestionarios, Vertex AI, el backend y la base de datos.

## Puntos a cuidar entre local y cloud

- **Puerto:** Cloud Run indica el puerto en la variable `PORT`, así que no se deja fijo en el código.
- **URL del extractor en el frontend:** en local se usa la de Docker Compose y en cloud la pública de Cloud Run. Se configura por variable de entorno.
- **CORS:** el extractor debe permitir el origen del frontend en ambos entornos.
- **Acceso público:** los servicios se despliegan con acceso sin autenticación para que la app sea accesible.
- **Credenciales del pipeline:** GitHub Actions se autentica en GCP sin guardar llaves en el repositorio.
- **Imágenes:** se publican en Artifact Registry, en la misma región que Cloud Run.

## Resultado esperado

Con un `docker compose up` la aplicación funciona en local, y con un push a GitHub queda desplegada en Cloud Run con la misma configuración.
