import type { ChartSpec } from "../types/chart";
import { publishChartAgentProgress } from "./chartAgentProgressStore";
import type { ProgressSnapshot } from "../types/progress";

export type ChartAgentRuntimeContext = {
  currentChart: ChartSpec | null;
  pageContext: Record<string, unknown>;
  userContext: {
    userId: string;
    tenantId: string;
  };
};

declare global {
  interface Window {
    __CHART_AGENT_CONTEXT__?: ChartAgentRuntimeContext;
    __CHART_AGENT_FETCH_PATCHED__?: boolean;
  }
}

export function syncChartAgentRuntimeContext(context: ChartAgentRuntimeContext) {
  window.__CHART_AGENT_CONTEXT__ = context;
}

export function installCopilotRuntimeContextPatch(runtimeUrl: string) {
  if (window.__CHART_AGENT_FETCH_PATCHED__) return;

  const originalFetch = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const context = window.__CHART_AGENT_CONTEXT__;
    if (!context || !isCopilotRuntimeRequest(input, runtimeUrl)) {
      return originalFetch(input, init);
    }

    const patchedInit = patchRequestInit(init, context);
    const response = await originalFetch(input, patchedInit);
    observeCopilotProgress(response);
    return response;
  };
  window.__CHART_AGENT_FETCH_PATCHED__ = true;
}

function isCopilotRuntimeRequest(input: RequestInfo | URL, runtimeUrl: string): boolean {
  const targetUrl = normalizeUrl(runtimeUrl);
  const requestUrl = normalizeUrl(input instanceof Request ? input.url : String(input));
  return Boolean(targetUrl && (requestUrl === targetUrl || requestUrl.startsWith(`${targetUrl}/`)));
}

function normalizeUrl(value: string): string {
  try {
    return new URL(value, window.location.origin).toString();
  } catch {
    return "";
  }
}

function patchRequestInit(
  init: RequestInit | undefined,
  context: ChartAgentRuntimeContext,
): RequestInit | undefined {
  if (!init?.body || typeof init.body !== "string") {
    return init;
  }

  try {
    const payload = JSON.parse(init.body);
    if (payload.method === "agent/run" && payload.body) {
      payload.body = {
        ...payload.body,
        forwardedProps: {
          ...(payload.body.forwardedProps ?? {}),
          ...context,
        },
        properties: {
          ...(payload.body.properties ?? {}),
          ...context,
        },
        chartAgentContext: context,
      };

      return {
        ...init,
        body: JSON.stringify(payload),
      };
    }

    if (isAgentRunBody(payload)) {
      return {
        ...init,
        body: JSON.stringify(withRuntimeContext(payload, context)),
      };
    }

    const variables = payload.variables ?? {};
    const data = variables.data ?? {};
    const metadata = data.metadata ?? {};

    payload.variables = {
      ...variables,
      properties: {
        ...(variables.properties ?? {}),
        ...context,
      },
      data: {
        ...data,
        properties: {
          ...(data.properties ?? {}),
          ...context,
        },
        metadata: {
          ...metadata,
          chartAgentContext: context,
        },
      },
    };

    return {
      ...init,
      body: JSON.stringify(payload),
    };
  } catch {
    return init;
  }
}

function isAgentRunBody(payload: unknown): payload is Record<string, unknown> {
  if (!payload || typeof payload !== "object") return false;
  const value = payload as Record<string, unknown>;
  return Array.isArray(value.messages) && typeof value.threadId === "string";
}

function withRuntimeContext(
  payload: Record<string, unknown>,
  context: ChartAgentRuntimeContext,
): Record<string, unknown> {
  const forwardedProps =
    payload.forwardedProps && typeof payload.forwardedProps === "object" && !Array.isArray(payload.forwardedProps)
      ? payload.forwardedProps
      : {};
  const properties =
    payload.properties && typeof payload.properties === "object" && !Array.isArray(payload.properties)
      ? payload.properties
      : {};

  return {
    ...payload,
    forwardedProps: {
      ...forwardedProps,
      ...context,
    },
    properties: {
      ...properties,
      ...context,
    },
    chartAgentContext: context,
  };
}

function observeCopilotProgress(response: Response) {
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
    // CopilotKit still owns the primary response stream; progress mirroring is best-effort.
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
