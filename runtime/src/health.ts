export type BackendHealthStatus = {
  reachable: boolean;
  status: "ok" | "unreachable";
  statusCode?: number;
  error?: string;
};

export type RuntimeHealthStatus = {
  status: "ok" | "degraded";
  runtime: "copilotkit-official-sdk-poc";
  backendUrl: string;
  backend: BackendHealthStatus;
};

type FetchLike = typeof fetch;

export async function runtimeHealthStatus(
  backendUrl: string,
  options: { fetchImpl?: FetchLike; timeoutMs?: number } = {}
): Promise<RuntimeHealthStatus> {
  const backend = await checkBackendHealth(backendUrl, options);
  return {
    status: backend.reachable ? "ok" : "degraded",
    runtime: "copilotkit-official-sdk-poc",
    backendUrl,
    backend
  };
}

export async function checkBackendHealth(
  backendUrl: string,
  options: { fetchImpl?: FetchLike; timeoutMs?: number } = {}
): Promise<BackendHealthStatus> {
  const fetchImpl = options.fetchImpl ?? fetch;
  const timeoutMs = options.timeoutMs ?? 2_000;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetchImpl(`${backendUrl.replace(/\/$/, "")}/health`, {
      method: "GET",
      signal: controller.signal
    });
    return {
      reachable: response.ok,
      status: response.ok ? "ok" : "unreachable",
      statusCode: response.status
    };
  } catch (error) {
    return {
      reachable: false,
      status: "unreachable",
      error: error instanceof Error ? error.message : String(error)
    };
  } finally {
    clearTimeout(timeout);
  }
}
