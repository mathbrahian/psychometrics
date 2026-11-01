import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// En desarrollo sirve /config.js igual que docker-entrypoint.sh en producción.
const runtimeConfig = () => ({
  name: 'runtime-config',
  configureServer(server) {
    server.middlewares.use('/config.js', (req, res) => {
      const config = { BACKEND_URL: process.env.BACKEND_URL ?? 'http://localhost:9090' }
      res.setHeader('Content-Type', 'application/javascript')
      res.end(`window.__CONFIG__ = ${JSON.stringify(config)};`)
    })
  },
})

export default defineConfig({
  plugins: [react(), runtimeConfig()],
})
