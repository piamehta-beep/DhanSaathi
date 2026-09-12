import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import { fileURLToPath, URL } from "node:url";

// The dev proxy keeps /api same-origin so the app behaves like production
// (where a reverse proxy would sit in front of both). VITE_API_BASE is only
// read when the app is served from somewhere the proxy can't reach.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "VITE_");
  return {
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg", "offline.html"],
      manifest: {
        name: "DhanSaathi",
        short_name: "DhanSaathi",
        description: "Aapke paise ka saathi",
        lang: "hi",
        start_url: "/",
        display: "standalone",
        background_color: "#faf8f4",
        theme_color: "#0f766e",
        icons: [
          { src: "icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png", purpose: "any maskable" },
        ],
      },
      workbox: {
        // App shell is precached; API responses are never cached by the SW —
        // TanStack Query holds the last successful responses in memory instead.
        navigateFallback: "/index.html",
        navigateFallbackDenylist: [/^\/api/, /^\/docs/, /^\/ui/],
        globPatterns: ["**/*.{js,css,html,svg,png}"],
      },
    }),
  ],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: env.VITE_API_BASE || "http://localhost:8010", changeOrigin: true },
    },
  },
  build: {
    target: "es2020",
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["react", "react-dom", "react-router-dom", "@tanstack/react-query"],
          i18n: ["i18next", "react-i18next"],
        },
      },
    },
  },
};
});
