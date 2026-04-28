import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],

  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },

  server: {
    port: 5174,
    host: true,
    proxy: {
      '/api': {
        #target: 'http://localhost:8000',
        target: 'https://devarchai.onrender.com'
        changeOrigin: true,
        secure: false,
        ws: true,
      },
      '/ws': {
        #target: 'ws://localhost:8000',
        target: 'ws://devarchai.onrender.com
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
