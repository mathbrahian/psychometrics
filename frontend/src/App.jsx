import { useState } from 'react'
import { EXTRACTOR_VERTEX_URL } from './config.js'

function App() {
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    if (!file) return

    const formData = new FormData()
    formData.append('file', file)

    setLoading(true)
    setResult('')
    try {
      const response = await fetch(`${EXTRACTOR_VERTEX_URL}/v1/questionnaires/extract`, {
        method: 'POST',
        body: formData,
      })
      const data = await response.json()
      setResult(`HTTP ${response.status}\n\n${JSON.stringify(data, null, 2)}`)
    } catch (error) {
      setResult(`No se pudo conectar con extractor-vertex (${EXTRACTOR_VERTEX_URL}): ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <h1>Extractor de cuestionarios</h1>
      <form onSubmit={handleSubmit}>
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
