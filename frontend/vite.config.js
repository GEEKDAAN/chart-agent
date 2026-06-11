import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backendProxyUrl = env.VITE_BACKEND_PROXY_URL || "http://localhost:8000";

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        "/chart-agent": backendProxyUrl,
        "/health": backendProxyUrl
      }
    }
  };
});
