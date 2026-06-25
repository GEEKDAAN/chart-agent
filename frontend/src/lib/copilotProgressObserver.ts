import { publishChartAgentProgress } from "./chartAgentProgressStore";
import { publishChartAgentAction } from "./chartAgentActionStore";
import {
  ACTION_CREATE_CHART,
  ACTION_ERROR,
  ACTION_UPDATE_CHART,
  COPILOT_TOOL_CALL_ARGS_EVENT,
  COPILOT_TOOL_CALL_RESULT_EVENT
} from "../domain/chartAgentProtocol";
import type { ChartAgentAction } from "../types/chart";
import type { ProgressSnapshot } from "../types/progress";

export function observeCopilotProgress(response: Response) {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("text/event-stream")) return;

  const body = response.clone().body;
  if (!body) return;

  void readProgressEvents(body);
}

async function readProgressEvents(body: ReadableStream<Uint8Array>) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";
      for (const part of parts) {
        publishProgressFromSseBlock(part);
      }
    }
    if (buffer) {
      publishProgressFromSseBlock(buffer);
    }
  } catch {
    // CopilotKit owns the primary response stream; progress mirroring is best-effort.
  }
}

function publishProgressFromSseBlock(block: string) {
  const dataLines = block
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trim());
  if (dataLines.length === 0) return;

  const event = safeParseJson(dataLines.join("\n"));
  if (!event || typeof event !== "object") return;

  const value = event as Record<string, unknown>;
  if (value.type === COPILOT_TOOL_CALL_ARGS_EVENT) {
    publishSnapshotFromUnknown(value.delta);
  }
  if (value.type === COPILOT_TOOL_CALL_RESULT_EVENT) {
    publishSnapshotFromUnknown(value.content);
    publishActionFromUnknown(value.content);
  }
}

function publishSnapshotFromUnknown(value: unknown) {
  const snapshot = typeof value === "string" ? safeParseJson(value) : value;
  if (isProgressSnapshot(snapshot)) {
    publishChartAgentProgress(snapshot);
  }
}

function safeParseJson(value: string): unknown {
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function isProgressSnapshot(value: unknown): value is ProgressSnapshot {
  if (!value || typeof value !== "object") return false;
  const snapshot = value as ProgressSnapshot;
  return typeof snapshot.progressId === "string" && Array.isArray(snapshot.steps);
}

function publishActionFromUnknown(value: unknown) {
  const payload = typeof value === "string" ? safeParseJson(value) : value;
  if (!payload || typeof payload !== "object") return;

  const record = payload as Record<string, unknown>;
  if (typeof record.actionId !== "string" || !isChartAgentAction(record.action)) return;
  publishChartAgentAction({ actionId: record.actionId, action: record.action });
}

function isChartAgentAction(value: unknown): value is ChartAgentAction {
  if (!value || typeof value !== "object") return false;

  const action = value as Record<string, unknown>;
  if (action.type === ACTION_CREATE_CHART) {
    return typeof action.message === "string" && Boolean(action.chart && typeof action.chart === "object");
  }
  if (action.type === ACTION_UPDATE_CHART) {
    return typeof action.message === "string" && typeof action.chartId === "string" && Boolean(action.patch && typeof action.patch === "object");
  }
  if (action.type === ACTION_ERROR) {
    return typeof action.message === "string" && typeof action.code === "string";
  }
  return false;
}
