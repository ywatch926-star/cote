import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: './',
  server: {
    host: true,
    allowedHosts: ['.monkeycode-ai.live', '.manus.computer'],
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  },
})
