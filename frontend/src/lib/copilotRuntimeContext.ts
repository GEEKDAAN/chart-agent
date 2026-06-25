import type { ChartSpec } from "../types/chart";
import {
  CHART_AGENT_CONTEXT_KEY,
  COPILOT_AGENT_RUN_METHOD,
  WINDOW_CHART_AGENT_CONTEXT_KEY,
  WINDOW_CHART_AGENT_FETCH_PATCHED_KEY
} from "../domain/chartAgentProtocol";
import { observeCopilotProgress } from "./copilotProgressObserver";

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
  window[WINDOW_CHART_AGENT_CONTEXT_KEY] = context;
}

export function installCopilotRuntimeContextPatch(runtimeUrl: string) {
  if (window[WINDOW_CHART_AGENT_FETCH_PATCHED_KEY]) return;

  const originalFetch = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const context = window[WINDOW_CHART_AGENT_CONTEXT_KEY];
    if (!context || !isCopilotRuntimeRequest(input, runtimeUrl)) {
      return originalFetch(input, init);
    }

    const patchedInit = patchRequestInit(init, context);
    const response = await originalFetch(input, patchedInit);
    observeCopilotProgress(response);
    return response;
  };
  window[WINDOW_CHART_AGENT_FETCH_PATCHED_KEY] = true;
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
    if (payload.method === COPILOT_AGENT_RUN_METHOD && payload.body) {
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
        [CHART_AGENT_CONTEXT_KEY]: context,
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
          [CHART_AGENT_CONTEXT_KEY]: context,
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
    [CHART_AGENT_CONTEXT_KEY]: context,
  };
}
