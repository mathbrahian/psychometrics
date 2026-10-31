# 11 - Frontend essentials

Esta etapa construye la interfaz que pide la prueba: el usuario adjunta un archivo, inicia el procesamiento y ve o descarga el resultado. Se avanza paso a paso, empezando por la conexión más simple posible con el extractor.

## Paso 1: subir el archivo y mostrar la respuesta en crudo

`frontend/src/App.jsx` tiene ahora:

- un `input` de archivo, que acepta `.pdf`, `.docx` y `.xlsx`;
- un botón **Subir**, deshabilitado mientras no haya archivo o mientras se procesa;
- la respuesta del extractor **sin formato**: el código HTTP y el JSON tal como llegan, dentro de un `<pre>`.

El archivo se envía con `FormData` a `POST {EXTRACTOR_VERTEX_URL}/v1/questionnaires/extract`, el mismo endpoint que se probó con los archivos `.http`.

Se muestra en crudo a propósito: el objetivo de este paso es comprobar que el flujo completo funciona (navegador → frontend → extractor → Vertex AI → navegador) antes de invertir en la presentación. También se muestran los errores tal cual, por ejemplo `HTTP 415` con su `error` y `detalle`.

### Dónde funciona

| Entorno   | Frontend                 | Extractor                        |
|-----------|--------------------------|----------------------------------|
| Local     | `http://localhost:3000`  | `http://localhost:8080` (compose)|
| Cloud Run | URL de Cloud Run         | URL de Cloud Run del extractor   |

La URL del extractor sale de `EXTRACTOR_VERTEX_URL`, que se lee al arrancar el contenedor. No hubo que cambiar nada de configuración.

Un frontend local **no** puede llamar al extractor de Cloud Run: el CORS del extractor solo permite las URLs del frontend en Cloud Run. Es lo esperado, porque cada entorno usa su propio par de servicios.

## Puertos: el frontend usa el 3000 en todos lados

Hasta ahora el frontend escuchaba en el `8080` dentro del contenedor, igual que el extractor, y solo en el host se mapeaba al `3000`. Para evitar confusiones, cada servicio tiene ahora un puerto propio, el mismo en todos los entornos:

| Servicio           | Puerto | Dónde se define                                                       |
|--------------------|--------|-----------------------------------------------------------------------|
| `extractor-vertex` | `8080` | `Dockerfile`, compose y pipeline                                      |
| `frontend`         | `3000` | `Dockerfile` (`ENV PORT=3000`), compose (`3000:3000`), Vite en modo desarrollo (`--port 3000`) y pipeline |

**En Cloud Run** el puerto lo decide el servicio, no la imagen: Cloud Run envía la variable `PORT` con el puerto configurado en el servicio, 8080 por defecto. Por eso el pipeline despliega cada servicio con su puerto explícito, usando una matriz:

```yaml
matrix:
  include:
    - service: extractor-vertex
      port: 8080
    - service: frontend
      port: 3000
```

```bash
gcloud run deploy ${{ matrix.service }} --image=$IMAGE --port=${{ matrix.port }} ...
```

La URL pública del frontend no cambia: el puerto es interno del contenedor.
