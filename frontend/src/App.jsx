import { useEffect, useState } from 'react'
import { EXTRACTOR_VERTEX_URL } from './config.js'

function App() {
  const [message, setMessage] = useState('Cargando...')

  useEffect(() => {
    fetch(`${EXTRACTOR_VERTEX_URL}/`)
      .then((res) => res.json())
      .then((data) => setMessage(data.message))
      .catch(() => setMessage(`No se pudo conectar con extractor-vertex (${EXTRACTOR_VERTEX_URL})`))
  }, [])

  return (
    <>
      <h1>Hola mundo desde frontend</h1>
      <p>{message}</p>
    </>
  )
}

export default App
