/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/shared/test/setup.ts'],
    env: {
      // Tests never call a real backend; this placeholder only satisfies the required setting.
      VITE_API_BASE_URL: 'http://api.test',
      // A fixed zone with daylight saving makes UTC-offset tests deterministic.
      TZ: 'America/Denver',
    },
    css: false,
    // Form tests type through user-event and render MUI and Leaflet in jsdom; with test files
    // running in parallel some take about 4 seconds, close to the 5-second default.
    testTimeout: 15_000,
  },
})
