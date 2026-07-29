import { defineConfig } from 'vite';

export default defineConfig({
  // No plugins needed — plain HTML/JS project
  root: '.',
  server: {
    port: 5173,
    open: false
  }
});
