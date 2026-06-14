import { useEffect, useMemo, useRef } from "react";
import {
  CopilotKitProvider,
  CopilotSidebar,
  useRenderTool,
  useAgent,
  useAgentContext,
  useConfigureSuggestions
} from "@copilotkit/react-core/v2";
import { z } from "zod";
import "@copilotkit/react-core/v2/styles.css";

import { copilotRuntimeUrl, isCopilotEnabled } from "../lib/config";
import { useChartAgentProgress } from "../lib/chartAgentProgressStore";
import {
  installCopilotRuntimeContextPatch,
  syncChartAgentRuntimeContext,
  type ChartAgentRuntimeContext
} from "../lib/copilotRuntimeContext";
import type { ChartAgentAction, ChartSpec } from "../types/chart";
import type { ProgressStep } from "../types/progress";

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

const progressStepSchema = z.object({
  id: z.string(),
  title: z.string(),
  detail: z.string(),
  status: z.enum(["pending", "running", "completed", "failed"])
});

const progressParametersSchema = z.object({
  progressId: z.string().optional(),
  steps: z.array(progressStepSchema)
});

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
      <ChartAgentProgressRenderer />
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

function ChartAgentProgressRenderer() {
  useRenderTool({
    name: "chartAgentProgress",
    parameters: progressParametersSchema,
    render: ({ status, parameters, result }) => {
      const resultSteps = readProgressSteps(result);
      const resultProgressId = readProgressId(result);
      const progressId = resultProgressId ?? parameters.progressId;
      const steps = resultSteps.length > 0 ? resultSteps : parameters.steps ?? [];
      return <ChatProgressSteps progressId={progressId} status={status} steps={steps} />;
    }
  });

  return null;
}

function ChatProgressSteps({
  progressId,
  status,
  steps
}: {
  progressId: string | undefined;
  status: string;
  steps: ProgressStep[];
}) {
  const streamedSnapshot = useChartAgentProgress(progressId);
  const visibleSteps = streamedSnapshot?.steps ?? steps;
  const label = status === "complete" ? "已完成" : "执行中";

  return (
    <section className="chat-progress" aria-label="执行步骤">
      <div className="chat-progress-header">
        <h3>执行步骤</h3>
        <span>{label}</span>
      </div>
      <ol className="chat-progress-list">
        {visibleSteps.map((step, index) => (
          <li className={`chat-progress-step chat-progress-step-${step.status}`} key={step.id}>
            <span className="chat-progress-index">{step.status === "completed" ? "✓" : index + 1}</span>
            <div>
              <strong>{step.title}</strong>
              <p>{step.detail}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

function readProgressSteps(result: unknown): ProgressStep[] {
  if (!result) return [];

  const parsed = typeof result === "string" ? safeJsonParse(result) : result;
  const validation = progressParametersSchema.safeParse(parsed);
  return validation.success ? validation.data.steps : [];
}

function readProgressId(result: unknown): string | undefined {
  if (!result) return undefined;

  const parsed = typeof result === "string" ? safeJsonParse(result) : result;
  const validation = progressParametersSchema.safeParse(parsed);
  return validation.success ? validation.data.progressId : undefined;
}

function safeJsonParse(value: string): unknown {
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
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
