import type { ChartAgentResponse, ChartSpec } from "../types/chart";

export async function sendChartMessage(message: string, currentChart: ChartSpec | null): Promise<ChartAgentResponse> {
  const response = await fetch("/chart-agent/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      conversationId: "demo",
      message,
      currentChart,
      pageContext: {},
      userContext: {
        userId: "u_demo",
        tenantId: "t_demo"
      }
    })
  });

  if (!response.ok) {
    throw new Error(`请求失败：${response.status}`);
  }
  return response.json();
}
