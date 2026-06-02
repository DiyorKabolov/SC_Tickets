import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: '/static/spa-react/',
  plugins: [react()],
  build: {
    outDir: '../../app/static/spa-react',
    emptyOutDir: true,
  },
})
