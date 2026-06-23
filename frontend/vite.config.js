import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backendProxyUrl = env.VITE_BACKEND_PROXY_URL || "http://localhost:8000";
  const copilotRuntimeProxyUrl = env.VITE_COPILOT_RUNTIME_PROXY_URL || backendProxyUrl;

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@segment/analytics-node": fileURLToPath(
          new URL("./src/lib/segmentAnalyticsNodeStub.ts", import.meta.url)
        )
      }
    },
    server: {
      port: 5173,
      proxy: {
        "/chart-agent": backendProxyUrl,
        "/copilotkit": copilotRuntimeProxyUrl,
        "/health": backendProxyUrl
      }
    },
    build: {
      chunkSizeWarningLimit: 2000,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes("node_modules/echarts") || id.includes("node_modules/zrender")) {
              return "echarts";
            }

            return undefined;
          }
        }
      }
    }
  };
});
