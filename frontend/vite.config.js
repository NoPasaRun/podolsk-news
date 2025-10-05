import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path'

export default {
  plugins: [react()],
  server: { port: 5173, host: true },
  preview: { port: 4173, host: true },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
}
