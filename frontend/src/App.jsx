import { useEffect, useState } from 'react'
import { BACKEND_URL } from './config.js'
import { NETWORK_ERROR, errorMessage, validateFile } from './errors.js'
import QuestionnaireView from './QuestionnaireView.jsx'

// Interfaz de psychometrics: inicio de sesión, extracción, vista del cuestionario y cuestionarios guardados.
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
  // Acción en curso, para mostrar el indicador de carga en el botón correspondiente.
  const [busy, setBusy] = useState('')
  const [dragging, setDragging] = useState(false)
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

  // Mientras el modal está abierto: Escape lo cierra y la página de fondo no se desplaza.
  useEffect(() => {
    if (!selected) return undefined
    const closeOnEscape = (event) => event.key === 'Escape' && setSelected(null)
    document.addEventListener('keydown', closeOnEscape)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', closeOnEscape)
      document.body.style.overflow = ''
    }
  }, [selected])

  async function request(path, options = {}) {
    setLoading(true)
    setError('')
    setNotice('')
    try {
      const headers = { ...(options.headers ?? {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) }
      const response = await fetch(`${BACKEND_URL}${path}`, { ...options, headers })
      const data = await readBody(response)
      if (!response.ok) {
        setError(errorMessage(response.status, data))
        // Si la sesión venció, se vuelve al inicio de sesión (el mensaje de error se mantiene).
        if (response.status === 401 && token) setToken('')
      }
      return { ok: response.ok, data }
    } catch (exception) {
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

  async function withBusy(key, action) {
    setBusy(key)
    try {
      return await action()
    } finally {
      setBusy('')
    }
  }

  async function handleLogin(event) {
    event.preventDefault()
    setBusy('login')
    const { ok, data } = await request('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ usuario: username, contrasena: password }),
    })
    setBusy('')
    if (ok) {
      setToken(data.access_token)
      setPassword('')
    }
  }

  // Limpia la consulta actual: el archivo elegido, el cuestionario detectado y los mensajes.
  function clearQuery() {
    setFile(null)
    setFileInputKey((key) => key + 1)
    setExtraction(null)
    setError('')
    setNotice('')
  }

  function logout() {
    setToken('')
    setExtraction(null)
    setSaved([])
    setSelected(null)
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

  const saveExtraction = () => withBusy('save', saveAll)

  async function saveAll() {
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

  const refreshSaved = () => withBusy('list', loadSaved)

  async function loadSaved() {
    const { ok, data } = await request('/v1/questionnaires')
    if (ok) setSaved(data)
  }

  const viewSaved = (id) => withBusy(`view:${id}`, () => fetchSaved(id))

  async function fetchSaved(id) {
    const { ok, data } = await request(`/v1/questionnaires/${id}`)
    if (ok) setSelected(data)
  }

  const deleteSaved = (id) => withBusy(`delete:${id}`, () => removeSaved(id))

  async function removeSaved(id) {
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

  function chooseFile(chosen) {
    if (!chosen) return
    setFile(chosen)
    setError('')
    setNotice('')
  }

  function handleDrop(event) {
    event.preventDefault()
    setDragging(false)
    chooseFile(event.dataTransfer.files[0])
  }

  const messages = (
    <>
      {error && (
        <div className="alert alert-error" role="alert">
          <span>⚠️</span>
          <span>
            <strong>Error:</strong> {error}
          </span>
        </div>
      )}
      {notice && (
        <div className="alert alert-success" role="status">
          <span>✓</span>
          <span>{notice}</span>
        </div>
      )}
    </>
  )

  const Spinner = ({ large = false }) => <span className={`spinner${large ? ' spinner-large' : ''}`} aria-hidden="true" />

  const navbar = (
    <header className="navbar">
      <div className="brand">
        <span className="brand-name">psychometrics</span>
        <span className="brand-tagline">Extractor de cuestionarios</span>
      </div>
      {token && (
        <div className="navbar-user">
          <span>{username}</span>
          <button className="btn btn-secondary btn-small" onClick={logout}>
            Cerrar sesión
          </button>
        </div>
      )}
    </header>
  )

  const hero = (
    <section className="hero">
      <span className="pill">Extracción de cuestionarios con IA</span>
      <h1>Digitaliza tus cuestionarios en segundos</h1>
      <p>Sube un PDF, Word o Excel y obtén sus ítems, alternativas y respuestas en un JSON estructurado.</p>
    </section>
  )

  if (!token) {
    return (
      <>
        {navbar}
        {hero}
        <main className="login">
          <form className="card" onSubmit={handleLogin}>
            <h2>Iniciar sesión</h2>
            <p className="card-subtitle">Ingresa con tu usuario para extraer y guardar cuestionarios.</p>
            <div className="field">
              <label htmlFor="username">Usuario</label>
              <input
                id="username"
                className="input"
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="password">Contraseña</label>
              <input
                id="password"
                className="input"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </div>
            {messages}
            <button className="btn btn-primary btn-block" type="submit" disabled={!username || !password || loading}>
              {busy === 'login' && <Spinner />}
              {busy === 'login' ? 'Ingresando...' : 'Iniciar sesión'}
            </button>
          </form>
        </main>
      </>
    )
  }

  const questionnaires = extractedQuestionnaires()
  const sheetErrors = extraction?.endpoint === 'extract-sheets' ? extraction.data.filter((sheet) => sheet.error) : []

  return (
    <>
      {navbar}
      {hero}
      <main className="container">
        <form className="card" onSubmit={handleExtract}>
          <h2>Nuevo cuestionario</h2>
          <p className="card-subtitle">Elige el modelo y el tipo de extracción, y sube tu archivo.</p>

          <div className="options-row">
            <div className="field">
              <span className="field-label">Modelo</span>
              <div className="segmented">
                <button type="button" className={provider === 'gemini' ? 'active' : ''} onClick={() => setProvider('gemini')}>
                  Gemini API
                </button>
                <button type="button" className={provider === 'vertex' ? 'active' : ''} onClick={() => setProvider('vertex')}>
                  Vertex AI
                </button>
              </div>
            </div>
            <div className="field">
              <span className="field-label">Extracción</span>
              <div className="segmented">
                <button type="button" className={endpoint === 'extract' ? 'active' : ''} onClick={() => setEndpoint('extract')}>
                  Un cuestionario
                </button>
                <button
                  type="button"
                  className={endpoint === 'extract-sheets' ? 'active' : ''}
                  onClick={() => setEndpoint('extract-sheets')}
                >
                  Todas las hojas del Excel
                </button>
              </div>
            </div>
          </div>

          <label
            className={`dropzone${dragging ? ' dragging' : ''}`}
            onDragOver={(event) => {
              event.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
          >
            <input
              key={fileInputKey}
              type="file"
              accept={endpoint === 'extract' ? '.pdf,.docx,.xlsx' : '.xlsx'}
              onChange={(event) => chooseFile(event.target.files[0])}
            />
            <span className="dropzone-icon">📄</span>
            <span className="dropzone-title">{file ? file.name : 'Arrastra tu archivo aquí o haz clic para elegirlo'}</span>
            <span className="dropzone-hint">
              {endpoint === 'extract' ? 'PDF, Word (.docx) o Excel (.xlsx)' : 'Excel (.xlsx), una hoja por cuestionario'} · máximo 10 MB
            </span>
          </label>

          <div className="actions">
            <button className="btn btn-primary" type="submit" disabled={!file || loading}>
              {extracting && <Spinner />}
              {extracting ? 'Procesando...' : 'Extraer cuestionario'}
            </button>
            <button
              className="btn btn-secondary"
              type="button"
              onClick={clearQuery}
              disabled={loading || (!file && !extraction && !error && !notice)}
            >
              Limpiar
            </button>
          </div>

          {!extracting && <div style={{ marginTop: 16 }}>{messages}</div>}

          {extracting && (
            <div className="processing" role="status">
              <Spinner large />
              <p className="processing-title">Analizando el documento con {provider === 'gemini' ? 'Gemini API' : 'Vertex AI'}...</p>
              <p className="processing-hint">Detectando ítems, alternativas y respuestas. Puede tardar hasta 30 segundos.</p>
              <div className="progress" />
              <div className="skeleton">
                <span />
                <span />
                <span />
              </div>
            </div>
          )}
        </form>

        {extraction && (
          <section className="card">
            <div className="card-header">
              <div>
                <h2>Cuestionario detectado</h2>
                <p className="card-subtitle">
                  {extraction.filename} · {extraction.provider === 'gemini' ? 'Gemini API' : 'Vertex AI'}
                </p>
              </div>
              <div className="actions" style={{ marginTop: 0 }}>
                <button
                  className="btn btn-secondary"
                  onClick={() => download(extraction.data, `${baseName(extraction.filename)}.json`)}
                >
                  Descargar JSON
                </button>
                <button className="btn btn-primary" onClick={saveExtraction} disabled={loading || questionnaires.length === 0}>
                  {busy === 'save' && <Spinner />}
                  {busy === 'save' ? 'Guardando...' : questionnaires.length > 1 ? `Guardar (${questionnaires.length})` : 'Guardar'}
                </button>
              </div>
            </div>
            {sheetErrors.map((sheet) => (
              <div key={sheet.hoja} className="alert alert-error" style={{ marginBottom: 12 }}>
                <span>⚠️</span>
                <span>
                  <strong>Hoja {sheet.hoja}:</strong> {sheet.error.detalle}
                </span>
              </div>
            ))}
            {questionnaires.map(({ name, questionnaire }) => (
              <div key={name} className="sheet">
                {questionnaires.length > 1 && <p className="sheet-name">{name}</p>}
                <QuestionnaireView questionnaire={questionnaire} />
              </div>
            ))}
          </section>
        )}

        <section className="card">
          <div className="card-header">
            <div>
              <h2>Cuestionarios guardados</h2>
              <p className="card-subtitle">Del más reciente al más antiguo.</p>
            </div>
            <button className="btn btn-secondary btn-small" onClick={refreshSaved} disabled={loading}>
              {busy === 'list' && <Spinner />}
              Actualizar
            </button>
          </div>
          {saved.length === 0 ? (
            <div className="empty">Todavía no hay cuestionarios guardados.</div>
          ) : (
            <ul className="saved-list">
              {saved.map((item) => (
                <li key={item.id} className={`saved-item${selected?.id === item.id ? ' selected' : ''}`}>
                  <div>
                    <p className="saved-title">{item.titulo ?? 'Cuestionario sin título'}</p>
                    <div className="saved-meta">
                      <span className="badge">{item.total_items} ítems</span>
                      <span className="badge badge-muted">{item.idioma}</span>
                      <span className="badge badge-muted">{item.proveedor === 'gemini' ? 'Gemini API' : 'Vertex AI'}</span>
                      <span className="badge badge-muted">{item.archivo_origen}</span>
                      <span className="badge badge-muted">{new Date(item.creado_en).toLocaleString()}</span>
                    </div>
                  </div>
                  <div className="saved-actions">
                    <button className="btn btn-secondary btn-small" onClick={() => viewSaved(item.id)} disabled={loading}>
                      {busy === `view:${item.id}` && <Spinner />}
                      Ver
                    </button>
                    <button className="btn btn-danger btn-small" onClick={() => deleteSaved(item.id)} disabled={loading}>
                      {busy === `delete:${item.id}` && <Spinner />}
                      Eliminar
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        {selected && (
          <section className="card">
            <div className="card-header">
              <div>
                <h2>Cuestionario guardado</h2>
                <p className="card-subtitle">
                  {selected.archivo_origen} · {selected.proveedor === 'gemini' ? 'Gemini API' : 'Vertex AI'} · guardado el{' '}
                  {new Date(selected.creado_en).toLocaleString()}
                </p>
              </div>
              <div className="actions" style={{ marginTop: 0 }}>
                <button
                  className="btn btn-secondary btn-small"
                  onClick={() => download(selected.cuestionario, `${baseName(selected.archivo_origen)}.json`)}
                >
                  Descargar JSON
                </button>
                <button className="btn btn-danger btn-small" onClick={() => deleteSaved(selected.id)} disabled={loading}>
                  Eliminar
                </button>
                <button className="btn btn-secondary btn-small" onClick={() => setSelected(null)}>
                  Cerrar
                </button>
              </div>
            </div>
            <QuestionnaireView questionnaire={selected.cuestionario} />
          </section>
        )}

      </main>

      {selected && (
        <div className="modal-backdrop" onClick={() => setSelected(null)}>
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-header">
              <div>
                <h2 id="modal-title">Cuestionario guardado</h2>
                <p className="card-subtitle">
                  {selected.archivo_origen} · {selected.proveedor === 'gemini' ? 'Gemini API' : 'Vertex AI'} · guardado el{' '}
                  {new Date(selected.creado_en).toLocaleString()}
                </p>
              </div>
              <button className="modal-close" onClick={() => setSelected(null)} aria-label="Cerrar">
                ×
              </button>
            </div>
            <div className="modal-body">
              <QuestionnaireView questionnaire={selected.cuestionario} />
            </div>
            <div className="modal-footer">
              <button
                className="btn btn-secondary"
                onClick={() => download(selected.cuestionario, `${baseName(selected.archivo_origen)}.json`)}
              >
                Descargar JSON
              </button>
              <button className="btn btn-danger" onClick={() => deleteSaved(selected.id)} disabled={loading}>
                {busy === `delete:${selected.id}` && <Spinner />}
                Eliminar
              </button>
              <button className="btn btn-primary" onClick={() => setSelected(null)}>
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
      <footer className="footer">psychometrics · Extracción de cuestionarios con Gemini</footer>
    </>
  )
}

export default App
