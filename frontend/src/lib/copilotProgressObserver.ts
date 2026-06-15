import { publishChartAgentProgress } from "./chartAgentProgressStore";
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
  if (value.type === "TOOL_CALL_ARGS") {
    publishSnapshotFromUnknown(value.delta);
  }
  if (value.type === "TOOL_CALL_RESULT") {
    publishSnapshotFromUnknown(value.content);
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
