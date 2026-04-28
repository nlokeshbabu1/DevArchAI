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
        target: 'https://devarchai.onrender.com',
        changeOrigin: true,
        secure: false,
        ws: true,
      },
      '/ws': {
        target: 'ws://devarchai.onrender.com',
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
