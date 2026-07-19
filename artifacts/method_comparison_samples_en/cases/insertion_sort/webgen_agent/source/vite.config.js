import { defineConfig } from 'vite';

export default defineConfig({
  // No plugins needed – this is a vanilla HTML/CSS/JS project
  root: '.',
  publicDir: 'public',
  build: {
    outDir: 'dist',
  },
});
