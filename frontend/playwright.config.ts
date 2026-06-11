import { defineConfig, devices } from "@playwright/test";

const frontendPort = Number(process.env.E2E_FRONTEND_PORT ?? 5178);
const backendPort = Number(process.env.E2E_BACKEND_PORT ?? 8004);

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: {
    timeout: 10_000
  },
  fullyParallel: false,
  reporter: [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "off"
  },
  webServer: [
    {
      command: `python -m uvicorn app.main:app --host 127.0.0.1 --port ${backendPort}`,
      cwd: "../backend",
      url: `http://127.0.0.1:${backendPort}/copilotkit/info`,
      reuseExistingServer: true,
      timeout: 60_000,
      env: {
        CHART_AGENT_LLM_MODE: "off"
      }
    },
    {
      command: `npm.cmd run dev -- --host 127.0.0.1 --port ${frontendPort}`,
      url: `http://127.0.0.1:${frontendPort}`,
      reuseExistingServer: true,
      timeout: 60_000,
      env: {
        VITE_COPILOT_RUNTIME_URL: "/copilotkit",
        VITE_BACKEND_PROXY_URL: `http://127.0.0.1:${backendPort}`
      }
    }
  ],
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        channel: "chrome"
      }
    }
  ]
});
