/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

/*
 * The app has to work with the phone in aeroplane mode, standing at a table in
 * a hall with no usable signal. Everything -- engine, boards, advice -- runs on
 * the device, so precaching the bundle makes the app fully functional offline
 * once it has been opened a single time.
 *
 * `base` is relative so the same build works from a subdirectory, which matters
 * both for static hosting and for the Capacitor APK wrapper later.
 */
export default defineConfig({
  base: './',
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg'],
      manifest: {
        name: 'KLIK KLAK',
        short_name: 'KLIK KLAK',
        description: 'Team pairing decisions, offline, at the table.',
        theme_color: '#14161a',
        background_color: '#14161a',
        display: 'standalone',
        orientation: 'portrait',
        start_url: './',
        scope: './',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png' },
          {
            /*
              A separate file, not icon-512 reused. Android crops maskable icons
              to a circle or squircle and only guarantees the centre 80%, so the
              raven is inset to 60% here. Pointing this at the full-bleed icon
              clipped the beak and crest on a round mask.
            */
            src: 'icon-maskable-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,ico,woff2}'],
        /*
         * A tap on the APK link is a navigation request, so without this the
         * service worker answers it from the precache with index.html and the
         * download silently produces the app again instead of the installer.
         * Let it go to the network.
         */
        navigateFallbackDenylist: [/\.apk$/],
      },
    }),
  ],

  /*
   * The About & Help screen imports the end-user guides straight from the
   * repository-root `docs/` directory, which sits one level above this Vite
   * root. The production build inlines those `?raw` strings and needs nothing
   * at runtime, but the dev server refuses to read outside the root unless it
   * is told to, so `tauri:dev` / `npm run dev` would 403 on the import. Allow
   * the parent; it still covers everything under `webapp/` as well.
   */
  server: {
    fs: {
      allow: ['..'],
    },
  },

  /*
   * The engine tests are genuinely CPU-bound: they run exhaustive searches over
   * thousands of generated boards. Alone each takes a couple of seconds, but
   * vitest runs files in parallel across every core, so under contention a test
   * that normally finishes in 2.6s can drift past vitest's 5s default and fail
   * as a timeout -- a red suite that says nothing about the code. Raising the
   * ceiling makes that class of false failure go away while still being far
   * below anything a genuine hang would take.
   */
  test: {
    testTimeout: 30_000,
    hookTimeout: 30_000,
  },
})
