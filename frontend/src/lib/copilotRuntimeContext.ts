import type { ChartSpec } from "../types/chart";

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
    return originalFetch(input, patchedInit);
  };
  window.__CHART_AGENT_FETCH_PATCHED__ = true;
}

function isCopilotRuntimeRequest(input: RequestInfo | URL, runtimeUrl: string): boolean {
  const targetUrl = normalizeUrl(runtimeUrl);
  const requestUrl = normalizeUrl(input instanceof Request ? input.url : String(input));
  return Boolean(targetUrl && requestUrl === targetUrl);
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
