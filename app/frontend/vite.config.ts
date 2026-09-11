import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      // Dev: forward API calls to FastAPI so the browser sees a single origin.
      proxy: {
        '/api': { target: env.VITE_API_PROXY ?? 'http://localhost:8000', changeOrigin: true },
      },
    },
  }
})
