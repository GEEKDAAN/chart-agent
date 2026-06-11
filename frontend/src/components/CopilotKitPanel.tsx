import { useEffect, useMemo, useRef } from "react";
import {
  CopilotKitProvider,
  CopilotSidebar,
  useAgent,
  useAgentContext,
  useConfigureSuggestions
} from "@copilotkit/react-core/v2";
import "@copilotkit/react-core/v2/styles.css";

import { copilotRuntimeUrl, isCopilotEnabled } from "../lib/config";
import {
  installCopilotRuntimeContextPatch,
  syncChartAgentRuntimeContext,
  type ChartAgentRuntimeContext
} from "../lib/copilotRuntimeContext";
import type { ChartAgentAction, ChartSpec } from "../types/chart";

type JsonSerializable =
  | string
  | number
  | boolean
  | null
  | JsonSerializable[]
  | { [key: string]: JsonSerializable };

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
  const runtimeContext = useMemo<ChartAgentRuntimeContext>(
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
    <CopilotKitProvider
      runtimeUrl={copilotRuntimeUrl}
      properties={runtimeContext}
      onError={({ error, code, context }) => {
        onApplyError(new Error(`CopilotKit 请求失败：${code} ${error.message} ${JSON.stringify(context)}`));
      }}
    >
      <CopilotRuntimeContextBridge context={runtimeContext} />
      <CopilotActionBridge onApplyAction={onApplyAction} onApplyError={onApplyError} />
      <CopilotSidebar
        agentId="chart-agent"
        defaultOpen
        width={420}
        labels={{
          modalHeaderTitle: "chart-agent",
          welcomeMessageText: "描述你想生成或修改的图表。",
          chatInputPlaceholder: "输入图表需求..."
        }}
      />
    </CopilotKitProvider>
  );
}

function CopilotRuntimeContextBridge({ context }: { context: ChartAgentRuntimeContext }) {
  useEffect(() => {
    syncChartAgentRuntimeContext(context);
    installCopilotRuntimeContextPatch(copilotRuntimeUrl);
  }, [context]);

  useAgentContext({
    description: "chart-agent 当前图表上下文",
    value: toJsonSerializable(context)
  });

  useAgentContext({
    description: "chart-agent 前端指令",
    value: buildInstructions(context.currentChart)
  });

  useConfigureSuggestions(
    {
      suggestions
    },
    [context.currentChart]
  );

  return null;
}

function CopilotActionBridge({
  onApplyAction,
  onApplyError
}: {
  onApplyAction: (action: ChartAgentAction) => void;
  onApplyError: (error: unknown) => void;
}) {
  const { agent } = useAgent({ agentId: "chart-agent" });
  const appliedMessageIds = useRef(new Set<string>());

  useEffect(() => {
    for (const message of agent.messages) {
      if (message.role !== "assistant" || typeof message.content !== "string") continue;
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
  }, [agent.messages, onApplyAction, onApplyError]);

  return null;
}

function toJsonSerializable(value: unknown): JsonSerializable {
  return JSON.parse(JSON.stringify(value)) as JsonSerializable;
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
