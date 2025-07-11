import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    watch: {
      // Exclude node_modules from the watcher to prevent "EMFILE: too many open files" error
      ignored: ['**/node_modules/**'],
    },
  },
})