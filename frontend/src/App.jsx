import { useEffect, useState } from 'react'
import { BACKEND_URL } from './config.js'
import { NETWORK_ERROR, errorMessage, validateFile } from './errors.js'
import QuestionnaireView from './QuestionnaireView.jsx'

// Versión plana: todas las funciones de la app, en HTML sin estilos. El diseño se hará después.
function App() {
  const [token, setToken] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [provider, setProvider] = useState('gemini')
  const [endpoint, setEndpoint] = useState('extract')
  const [file, setFile] = useState(null)
  // Cambiar la key del input de archivo lo vuelve a crear vacío: es la forma de limpiarlo en React.
  const [fileInputKey, setFileInputKey] = useState(0)
  const [loading, setLoading] = useState(false)
  const [extracting, setExtracting] = useState(false)
  const [log, setLog] = useState('')
  // Mensajes visibles: error de la última acción o confirmación de que salió bien.
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [extraction, setExtraction] = useState(null)
  const [saved, setSaved] = useState([])
  const [selected, setSelected] = useState(null)

  // Al iniciar sesión se carga la lista de cuestionarios guardados.
  useEffect(() => {
    if (token) loadSaved()
  }, [token])

  async function request(path, options = {}) {
    setLoading(true)
    setError('')
    setNotice('')
    try {
      const headers = { ...(options.headers ?? {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) }
      const response = await fetch(`${BACKEND_URL}${path}`, { ...options, headers })
      const data = await readBody(response)
      setLog(`${options.method ?? 'GET'} ${path} → HTTP ${response.status}\n\n${JSON.stringify(data, null, 2)}`)
      if (!response.ok) {
        setError(errorMessage(response.status, data))
        // Si la sesión venció, se vuelve al inicio de sesión (el mensaje de error se mantiene).
        if (response.status === 401 && token) setToken('')
      }
      return { ok: response.ok, data }
    } catch (exception) {
      setLog(`No se pudo conectar con el backend (${BACKEND_URL}): ${exception.message}`)
      setError(NETWORK_ERROR)
      return { ok: false, data: null }
    } finally {
      setLoading(false)
    }
  }

  // Algunas respuestas no traen JSON: un 204, o un error de la infraestructura en HTML.
  async function readBody(response) {
    if (response.status === 204) return null
    const text = await response.text()
    try {
      return JSON.parse(text)
    } catch {
      return { texto: text.slice(0, 500) }
    }
  }

  async function handleLogin(event) {
    event.preventDefault()
    const { ok, data } = await request('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ usuario: username, contrasena: password }),
    })
    if (ok) {
      setToken(data.access_token)
      setPassword('')
    }
  }

  // Limpia la consulta actual: el archivo elegido, el cuestionario detectado y la última respuesta.
  function clearQuery() {
    setFile(null)
    setFileInputKey((key) => key + 1)
    setExtraction(null)
    setLog('')
    setError('')
    setNotice('')
  }

  function logout() {
    setToken('')
    setExtraction(null)
    setSaved([])
    setSelected(null)
    setLog('')
    setError('')
    setNotice('')
  }

  async function handleExtract(event) {
    event.preventDefault()
    if (!file) return
    setExtraction(null)
    const invalid = validateFile(file, endpoint)
    if (invalid) {
      setError(invalid)
      setNotice('')
      return
    }
    const formData = new FormData()
    formData.append('file', file)
    setExtracting(true)
    const { ok, data } = await request(`/v1/questionnaires/${endpoint}?proveedor=${provider}`, {
      method: 'POST',
      body: formData,
    })
    setExtracting(false)
    if (!ok) return
    setExtraction({ endpoint, provider, filename: file.name, data })
    if (endpoint === 'extract') {
      setNotice(`Cuestionario detectado: ${data.total_items} ítems.`)
    } else {
      const failed = data.filter((sheet) => sheet.error).length
      const message = `Se procesaron ${data.length} hojas.`
      if (failed === data.length) setError(`${message} Ninguna se pudo extraer; vea el detalle de cada hoja.`)
      else setNotice(failed ? `${message} ${failed} con error; vea el detalle abajo.` : message)
    }
  }

  // Un resultado de /extract es un cuestionario; uno de /extract-sheets, una lista de hojas.
  function extractedQuestionnaires() {
    if (!extraction) return []
    if (extraction.endpoint === 'extract') return [{ name: extraction.filename, questionnaire: extraction.data }]
    return extraction.data
      .filter((sheet) => sheet.cuestionario)
      .map((sheet) => ({ name: `${extraction.filename} (${sheet.hoja})`, questionnaire: sheet.cuestionario }))
  }

  async function saveExtraction() {
    const questionnaires = extractedQuestionnaires()
    let savedCount = 0
    for (const { name, questionnaire } of questionnaires) {
      const { ok } = await request('/v1/questionnaires', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proveedor: extraction.provider, archivo_origen: name, cuestionario: questionnaire }),
      })
      if (!ok) break
      savedCount += 1
    }
    if (savedCount === 0) return
    await loadSaved()
    if (savedCount === questionnaires.length) {
      setNotice(savedCount === 1 ? 'Cuestionario guardado.' : `Se guardaron ${savedCount} cuestionarios.`)
    } else {
      setError(`Se guardaron ${savedCount} de ${questionnaires.length} cuestionarios; los demás no se pudieron guardar.`)
    }
  }

  async function loadSaved() {
    const { ok, data } = await request('/v1/questionnaires')
    if (ok) setSaved(data)
  }

  async function viewSaved(id) {
    const { ok, data } = await request(`/v1/questionnaires/${id}`)
    if (ok) setSelected(data)
  }

  async function deleteSaved(id) {
    const { ok } = await request(`/v1/questionnaires/${id}`, { method: 'DELETE' })
    if (ok) {
      if (selected?.id === id) setSelected(null)
      await loadSaved()
      setNotice('Cuestionario eliminado.')
    }
  }

  function download(data, filename) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)
  }

  const baseName = (filename) => filename.replace(/\.[^.]+$/, '')

  const messages = (
    <>
      {error && (
        <p role="alert">
          <strong>Error:</strong> {error}
        </p>
      )}
      {notice && <p role="status">{notice}</p>}
    </>
  )

  if (!token) {
    return (
      <>
        <h1>Extractor de cuestionarios</h1>
        <form onSubmit={handleLogin}>
          <input placeholder="Usuario" value={username} onChange={(event) => setUsername(event.target.value)} />
          <input
            type="password"
            placeholder="Contraseña"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <button type="submit" disabled={!username || !password || loading}>
            {loading ? 'Ingresando...' : 'Iniciar sesión'}
          </button>
        </form>
        {messages}
      </>
    )
  }

  return (
    <>
      <h1>Extractor de cuestionarios</h1>
      <button onClick={logout}>Cerrar sesión</button>
      {messages}

      <h2>Extraer</h2>
      <form onSubmit={handleExtract}>
        <select value={provider} onChange={(event) => setProvider(event.target.value)}>
          <option value="gemini">Gemini API</option>
          <option value="vertex">Vertex AI</option>
        </select>
        <select value={endpoint} onChange={(event) => setEndpoint(event.target.value)}>
          <option value="extract">Un cuestionario (PDF, .docx o .xlsx)</option>
          <option value="extract-sheets">Todas las hojas del Excel (.xlsx)</option>
        </select>
        <input
          key={fileInputKey}
          type="file"
          accept=".pdf,.docx,.xlsx"
          onChange={(event) => setFile(event.target.files[0])}
        />
        <button type="submit" disabled={!file || loading}>
          {loading ? 'Procesando...' : 'Subir'}
        </button>
        <button type="button" onClick={clearQuery} disabled={loading || (!file && !extraction && !log)}>
          Limpiar
        </button>
      </form>
      {extracting && <p role="status">Procesando... la extracción puede tardar hasta 30 segundos.</p>}
      {extraction && (
        <>
          <h2>Cuestionario detectado</h2>
          <p>
            <button onClick={() => download(extraction.data, `${baseName(extraction.filename)}.json`)}>
              Descargar JSON
            </button>
            <button onClick={saveExtraction} disabled={loading || extractedQuestionnaires().length === 0}>
              Guardar ({extractedQuestionnaires().length})
            </button>
          </p>
          {extraction.endpoint === 'extract-sheets' &&
            extraction.data
              .filter((sheet) => sheet.error)
              .map((sheet) => (
                <p key={sheet.hoja}>
                  Hoja {sheet.hoja}: error {sheet.error.error}. {sheet.error.detalle}
                </p>
              ))}
          {extractedQuestionnaires().map(({ name, questionnaire }) => (
            <div key={name}>
              <p>Archivo: {name}</p>
              <QuestionnaireView questionnaire={questionnaire} />
              <hr />
            </div>
          ))}
        </>
      )}

      <h2>Cuestionarios guardados</h2>
      <button onClick={loadSaved} disabled={loading}>
        Actualizar lista
      </button>
      <ul>
        {saved.map((item) => (
          <li key={item.id}>
            {item.titulo ?? '(sin título)'} | {item.idioma} | {item.total_items} ítems | {item.proveedor} |{' '}
            {item.archivo_origen} | {new Date(item.creado_en).toLocaleString()}{' '}
            <button onClick={() => viewSaved(item.id)}>Ver</button>
            <button onClick={() => deleteSaved(item.id)}>Eliminar</button>
          </li>
        ))}
      </ul>
      {saved.length === 0 && <p>No hay cuestionarios guardados.</p>}
      {selected && (
        <>
          <h2>Cuestionario guardado</h2>
          <p>
            Archivo: {selected.archivo_origen} | Proveedor: {selected.proveedor} | Guardado:{' '}
            {new Date(selected.creado_en).toLocaleString()}{' '}
            <button onClick={() => download(selected.cuestionario, `${baseName(selected.archivo_origen)}.json`)}>
              Descargar JSON
            </button>
            <button onClick={() => deleteSaved(selected.id)}>Eliminar</button>
            <button onClick={() => setSelected(null)}>Cerrar</button>
          </p>
          <QuestionnaireView questionnaire={selected.cuestionario} />
        </>
      )}

      <details>
        <summary>Última respuesta del backend</summary>
        <pre>{log}</pre>
      </details>
    </>
  )
}

export default App
