import { resolve } from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        wechat: resolve(__dirname, "wechat/index.html"),
      },
    },
  },
  server: {
    host: "0.0.0.0",
    port: 8501,
    // Proxy API calls to the backend orchestrator so that
    // `npm run dev` works without a separate nginx setup.
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8766",
        changeOrigin: true,
      },
      "/health": {
        target: "http://127.0.0.1:8766",
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: "0.0.0.0",
    port: 8501,
  },
});
