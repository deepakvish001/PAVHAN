import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The API, uploaded media and seed artwork are all proxied through the dev
// server so the app runs on one origin. That matters for more than tidiness:
// getUserMedia and the Web Speech API only work in a secure context, and
// "same origin as localhost" is the easiest way to stay in one.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/media': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/seed': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  build: { outDir: 'dist', sourcemap: false },
})
