import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: '/static/spa-react-build/',
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:5000',
      '/static/event_covers': 'http://127.0.0.1:5000',
      '/static/design': 'http://127.0.0.1:5000',
    },
  },
  build: {
    outDir: '../spa-react-build',
    emptyOutDir: true,
  },
})
