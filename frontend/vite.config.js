import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"
import path from "path"

export default defineConfig({
  base: "/assets/event_management/frontend/",
  plugins: [vue()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  build: {
    outDir: "../event_management/public/frontend",
    emptyOutDir: true,
    target: "esnext",
    rollupOptions: {
      output: {
        entryFileNames: "assets/index.js",
        chunkFileNames: "assets/[name].js",
        assetFileNames: "assets/index.[ext]",
      },
    },
  },
  server: {
    port: 8080,
    proxy: {
      "^/(app|api|assets|files|private)": {
        target: "http://127.0.0.1:8000",
        ws: true,
      },
    },
  },
})
