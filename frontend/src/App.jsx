import { useState } from 'react'
import { BACKEND_URL } from './config.js'

// Versión en crudo: comprueba el flujo completo navegador → backend → extractor → modelo.
function App() {
  const [token, setToken] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [provider, setProvider] = useState('gemini')
  const [endpoint, setEndpoint] = useState('extract')
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState('')

  async function request(path, options) {
    setLoading(true)
    setResult('')
    try {
      const response = await fetch(`${BACKEND_URL}${path}`, options)
      const data = await response.json()
      setResult(`HTTP ${response.status}\n\n${JSON.stringify(data, null, 2)}`)
      return response.ok ? data : null
    } catch (error) {
      setResult(`No se pudo conectar con el backend (${BACKEND_URL}): ${error.message}`)
      return null
    } finally {
      setLoading(false)
    }
  }

  async function handleLogin(event) {
    event.preventDefault()
    const data = await request('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ usuario: username, contrasena: password }),
    })
    if (data) {
      setToken(data.access_token)
      setPassword('')
    }
  }

  async function handleExtract(event) {
    event.preventDefault()
    if (!file) return
    const formData = new FormData()
    formData.append('file', file)
    await request(`/v1/questionnaires/${endpoint}?proveedor=${provider}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    })
  }

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
        <pre>{result}</pre>
      </>
    )
  }

  return (
    <>
      <h1>Extractor de cuestionarios</h1>
      <button onClick={() => setToken('')}>Cerrar sesión</button>
      <form onSubmit={handleExtract}>
        <select value={provider} onChange={(event) => setProvider(event.target.value)}>
          <option value="gemini">Gemini API</option>
          <option value="vertex">Vertex AI</option>
        </select>
        <select value={endpoint} onChange={(event) => setEndpoint(event.target.value)}>
          <option value="extract">Un cuestionario (PDF, .docx o .xlsx)</option>
          <option value="extract-sheets">Todas las hojas del Excel (.xlsx)</option>
        </select>
        <input type="file" accept=".pdf,.docx,.xlsx" onChange={(event) => setFile(event.target.files[0])} />
        <button type="submit" disabled={!file || loading}>
          {loading ? 'Procesando...' : 'Subir'}
        </button>
      </form>
      <pre>{result}</pre>
    </>
  )
}

export default App
