import { useEffect, useMemo, useRef } from "react";
import { CopilotKit, useCopilotMessagesContext } from "@copilotkit/react-core";
import { CopilotSidebar } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";

import { copilotRuntimeUrl, isCopilotEnabled } from "../lib/config";
import type { ChartAgentAction, ChartSpec } from "../types/chart";

type CopilotKitPanelProps = {
  chart: ChartSpec | null;
  onApplyAction: (action: ChartAgentAction) => void;
  onApplyError: (error: unknown) => void;
};

const suggestions = [
  { title: "生成图表", message: "看最近30天各渠道销售额" },
  { title: "修改样式", message: "把抖音改成红色" },
  { title: "新增指标", message: "加一列利润率" },
  { title: "切换类型", message: "换成折线图" }
];

export function CopilotKitPanel({ chart, onApplyAction, onApplyError }: CopilotKitPanelProps) {
  const properties = useMemo(
    () => ({
      currentChart: chart,
      pageContext: { source: "copilotkit" },
      userContext: { userId: "u_demo", tenantId: "t_demo" }
    }),
    [chart]
  );

  if (!isCopilotEnabled) {
    return null;
  }

  return (
    <CopilotKit runtimeUrl={copilotRuntimeUrl} properties={properties}>
      <CopilotActionBridge onApplyAction={onApplyAction} onApplyError={onApplyError} />
      <CopilotSidebar
        defaultOpen={false}
        instructions={buildInstructions(chart)}
        labels={{
          title: "chart-agent",
          initial: "描述你想生成或修改的图表。"
        }}
        suggestions={suggestions}
      />
    </CopilotKit>
  );
}

function CopilotActionBridge({
  onApplyAction,
  onApplyError
}: {
  onApplyAction: (action: ChartAgentAction) => void;
  onApplyError: (error: unknown) => void;
}) {
  const { messages } = useCopilotMessagesContext();
  const appliedMessageIds = useRef(new Set<string>());

  useEffect(() => {
    for (const message of messages) {
      if (!message.isTextMessage() || message.role !== "assistant") continue;
      if (appliedMessageIds.current.has(message.id)) continue;

      const action = extractActionMarker(message.content);
      if (!action) continue;

      try {
        onApplyAction(action);
      } catch (error) {
        onApplyError(error);
      } finally {
        appliedMessageIds.current.add(message.id);
      }
    }
  }, [messages, onApplyAction, onApplyError]);

  return null;
}

function extractActionMarker(content: string): ChartAgentAction | null {
  const match = content.match(/<!--\s*chart-agent-action:([A-Za-z0-9+/=]+)\s*-->/);
  if (!match) return null;

  try {
    const bytes = Uint8Array.from(atob(match[1]), (character) => character.charCodeAt(0));
    return JSON.parse(new TextDecoder().decode(bytes)) as ChartAgentAction;
  } catch {
    return null;
  }
}

function buildInstructions(chart: ChartSpec | null): string {
  const chartContext = chart
    ? JSON.stringify(
        {
          id: chart.id,
          title: chart.title,
          chartType: chart.chartType,
          columns: chart.data.columns,
          encoding: chart.encoding,
          style: chart.style
        },
        null,
        2
      )
    : "当前还没有图表。";

  return [
    "你是 chart-agent 的前端 CopilotKit 入口。",
    "只帮助用户表达图表生成或编辑需求。",
    "不要生成 React、SQL 或 ECharts option。",
    "后端只接受自然语言消息和当前 ChartSpec 上下文。",
    `当前图表上下文：${chartContext}`
  ].join("\n");
}
