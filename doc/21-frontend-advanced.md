# 21 - Frontend

El frontend de la aplicación: inicio de sesión, extracción con cualquiera de los dos modelos, vista del cuestionario, descarga del JSON y cuestionarios guardados. Consume solo el **backend** (ver [16 - Backend](16-backend.md)); no conoce las URLs de los extractores.

Se construyó en dos pasos: primero una versión **plana**, con todas las funciones en HTML sin estilos, para comprobar el flujo completo; después, el **diseño solo con CSS**.

## Funciones

`frontend/src/App.jsx`:

| Sección | Qué hace | Endpoint del backend |
|---|---|---|
| Inicio de sesión | Usuario y contraseña. El token queda en memoria; **Cerrar sesión** lo descarta. Si el backend responde `401` (token vencido), se vuelve al login. | `POST /auth/login` |
| Extraer | Proveedor (Gemini API o Vertex AI), modo (un cuestionario o todas las hojas del Excel) y archivo. **Limpiar** borra la consulta actual: el archivo elegido, el cuestionario detectado y los mensajes. | `POST /v1/questionnaires/extract` o `/extract-sheets` |
| Cuestionario detectado | El cuestionario en pantalla, **Descargar JSON** (requisito de la prueba) y **Guardar**. De un Excel por hojas se muestra y se guarda un cuestionario por cada hoja procesada con éxito, y se listan los errores de las demás. | `POST /v1/questionnaires` |
| Cuestionarios guardados | Lista con título, idioma, ítems, proveedor, archivo y fecha, que se carga al iniciar sesión. **Ver** abre el cuestionario en un modal, con **Descargar JSON**, **Eliminar** y **Cerrar**. | `GET`, `GET /{id}` y `DELETE /{id}` |

El cuestionario se muestra con `frontend/src/QuestionnaireView.jsx`: título, idioma y cantidad de ítems; y por cada ítem, su enunciado, su tipo, sus alternativas y la respuesta correcta, si el documento la indica. El mismo componente sirve para el resultado de la extracción y para un cuestionario guardado. Se verificó renderizándolo con el resultado del caso `03-tipo-pdf`, que incluye los 5 tipos de ítem.

La descarga se genera en el navegador (`Blob` y un enlace temporal), sin otra llamada al backend.

## Diseño solo con CSS

Sobre la versión plana se agregó el diseño, **sin librerías de componentes ni frameworks de CSS**: un solo archivo, `frontend/src/styles.css`, con variables de CSS para la paleta.

- **Tipografía Poppins** (Google Fonts) y **paleta violeta**: banda principal con degradado, tarjetas blancas con sombra suave y botones primarios violeta.
- **Barra superior** con el nombre de la app, **psychometrics**, el usuario y **Cerrar sesión**.
- **Extracción:** selectores segmentados para el modelo (Gemini API o Vertex AI) y el modo (un cuestionario o todas las hojas), y una **zona para arrastrar y soltar** el archivo, que también se abre con un clic.
- **Cuestionario:** cada ítem en una tarjeta numerada, con su tipo como etiqueta y la **respuesta correcta resaltada en verde** con un ✓.
- **Cuestionarios guardados:** lista con etiquetas (ítems, idioma, proveedor, archivo y fecha). **Ver** abre un **modal**: se cierra con **Cerrar**, con la tecla Escape o con un clic fuera de él; solo el contenido se desplaza, y el encabezado y los botones quedan siempre a la vista.
- **Carga:**
  - cada botón muestra un spinner mientras su acción está en curso (iniciar sesión, extraer, guardar, actualizar, ver y eliminar);
  - mientras se extrae, un panel con spinner, el modelo que se está usando, una barra de progreso indeterminada y un esqueleto animado del resultado.
- **Mensajes:** errores en un recuadro rojo y confirmaciones en uno verde.
- **Diseño adaptable:** en pantallas angostas, la lista de guardados pasa a una sola columna.

El panel de depuración con la respuesta en crudo del backend se quitó: ya no hace falta, porque los errores se muestran en la interfaz.

## Manejo de errores en la UI

La prueba pide **informar** si no se detectan ítems, si el formato es inválido o si ocurre un error. Antes, el error solo quedaba en la respuesta en crudo, plegada. Ahora cada acción muestra un mensaje visible:

- **Error** (`role="alert"`, precedido de **Error:**): aparece arriba, tanto en el inicio de sesión como en la app. Todavía sin estilos.
- **Confirmación** (`role="status"`): por ejemplo *"Cuestionario detectado: 12 ítems."*, *"Cuestionario guardado."* o *"Cuestionario eliminado."*
- **Procesando:** mientras se extrae, *"Procesando... la extracción puede tardar hasta 30 segundos."*

`frontend/src/errors.js` convierte cada respuesta en un mensaje:

| Respuesta                                              | Mensaje                                                           |
|--------------------------------------------------------|-------------------------------------------------------------------|
| `{ "error", "detalle" }` del backend o de un extractor | El `detalle`, que ya está escrito para el usuario: *"El formato '.doc' no está soportado."*, *"No se detectaron ítems en el documento."*, *"Usuario o contraseña incorrectos."* |
| `422` de validación de FastAPI (`{ "detail": [...] }`) | *"Los datos enviados no son válidos. Revise: proveedor."*         |
| Respuesta sin JSON (por ejemplo, un `502` en HTML)     | Un mensaje según el código HTTP                                   |
| Sin conexión con el backend                            | *"No se pudo conectar con el servidor. Revise su conexión o intente más tarde."* |

**Validación en el navegador antes de subir el archivo:** extensión según la opción (`.pdf`, `.docx` y `.xlsx` para un cuestionario; solo `.xlsx` para todas las hojas), archivo vacío y tamaño máximo de 10 MB. Así se avisa al instante, sin esperar al servidor. El backend vuelve a validar igual, porque la validación del navegador se puede saltar.

**Casos particulares:**

- **Sesión vencida:** con un `401` en medio de la sesión, se vuelve al inicio de sesión y el mensaje *"La sesión venció. Inicie sesión de nuevo."* se mantiene visible.
- **Excel por hojas:** si algunas hojas fallan, se informa cuántas, y el detalle de cada una aparece junto a su resultado. Si fallan todas, se muestra como error.
- **Guardar varias hojas:** si alguna no se puede guardar, se indica cuántas se guardaron de cuántas.

Se verificó la lógica de `errors.js` en Node con los casos de la tabla y con la validación de archivos (`.doc`, `.pdf` en la opción de hojas, archivo vacío, archivo de más de 10 MB y un `.XLSX` válido).

La configuración en tiempo de ejecución pasó de `EXTRACTOR_VERTEX_URL` a **`BACKEND_URL`** (`config.js`, `docker-entrypoint.sh`, `vite.config.js`, `Dockerfile` y compose). El frontend ya no conoce las URLs de los extractores.

## Videos

- [Video 9](https://youtu.be/HHIYMdQgaWQ): frontend plano con todas las funciones.
- [Video 10](https://www.youtube.com/watch?v=7phXoXy2F5g): evolución del frontend solo con CSS.
