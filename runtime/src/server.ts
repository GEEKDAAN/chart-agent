import express from "express";
import { CopilotRuntime } from "@copilotkit/runtime/v2";
import { createCopilotExpressHandler } from "@copilotkit/runtime/v2/express";

import { ChartAgent } from "./chart-agent.js";
import { runtimeHealthStatus } from "./health.js";

const port = Number(process.env.PORT ?? 8004);
const backendUrl = normalizeUrl(process.env.CHART_AGENT_BACKEND_URL, "http://127.0.0.1:8000");

const runtime = new CopilotRuntime({
  agents: {
    "chart-agent": new ChartAgent({ backendUrl })
  }
});

const app = express();

app.get("/health", async (_request, response) => {
  const health = await runtimeHealthStatus(backendUrl);
  response.status(health.status === "ok" ? 200 : 503).json(health);
});

app.use(
  createCopilotExpressHandler({
    runtime,
    basePath: "/copilotkit",
    mode: "multi-route",
    cors: true
  })
);

app.listen(port, "127.0.0.1", () => {
  console.log(`chart-agent CopilotKit Runtime PoC listening on http://127.0.0.1:${port}`);
  console.log(`proxying ChartAgent business requests to ${backendUrl}`);
});

function normalizeUrl(value: string | undefined, fallback: string): string {
  if (!value || value === "undefined" || value === "null") {
    return fallback;
  }
  return value;
}
