import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxy em dev: evita CORS sem precisar alterar o backend.
// Qualquer request para /buses/* ou /registrations/* é repassado
// para o Uvicorn rodando em localhost:8000.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/buses': 'http://localhost:8000',
      '/registrations': 'http://localhost:8000',
    },
  },
})
