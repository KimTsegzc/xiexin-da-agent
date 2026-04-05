import { resolve } from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const backendPort =
  process.env.XIEXIN_BACKEND_PORT ||
  process.env.BACKEND_PORT ||
  (process.env.NODE_ENV === "production" ? "8766" : "8765");
const backendTarget = `http://127.0.0.1:${backendPort}`;

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
    // Launcher local default is 8765.
    // Cloud/systemd service runs with NODE_ENV=production and defaults to 8766.
    // Either side can override via XIEXIN_BACKEND_PORT or BACKEND_PORT.
    proxy: {
      "/api": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/health": {
        target: backendTarget,
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: "0.0.0.0",
    port: 8501,
  },
});
