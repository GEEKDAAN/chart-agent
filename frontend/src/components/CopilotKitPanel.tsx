import { useEffect, useMemo, useRef } from "react";
import {
  CopilotKitProvider,
  CopilotSidebar,
  useRenderTool,
  useAgentContext,
  useConfigureSuggestions
} from "@copilotkit/react-core/v2";
import { z } from "zod";
import "@copilotkit/react-core/v2/styles.css";

import {
  ACTION_CREATE_CHART,
  ACTION_ERROR,
  ACTION_UPDATE_CHART,
  CHART_AGENT_ACTION_TOOL,
  CHART_AGENT_ID,
  CHART_AGENT_MUTATING_ACTION_TYPES,
  CHART_AGENT_PROGRESS_TOOL,
  CHART_AGENT_UI_BLOCKS_TOOL,
  COLUMN_TYPES,
  DEFAULT_PAGE_CONTEXT,
  DEFAULT_USER_CONTEXT,
  UI_BLOCK_DATA_TABLE,
  UI_BLOCK_INSIGHT_CARD,
  UI_BLOCK_METRIC_SUMMARY,
  UI_BLOCK_SUGGESTED_ACTIONS
} from "../domain/chartAgentProtocol";
import { copilotRuntimeUrl, isCopilotEnabled } from "../lib/config";
import { submitCopilotChatMessage } from "../lib/copilotChatSubmit";
import { useLatestChartAgentAction } from "../lib/chartAgentActionStore";
import { useChartAgentProgress } from "../lib/chartAgentProgressStore";
import {
  installCopilotRuntimeContextPatch,
  syncChartAgentRuntimeContext,
  type ChartAgentRuntimeContext
} from "../lib/copilotRuntimeContext";
import type { ChartAgentAction, ChartAgentUiBlock, ChartSpec } from "../types/chart";
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

const actionParametersSchema = z.object({
  actionId: z.string().optional(),
  actionType: z.enum(CHART_AGENT_MUTATING_ACTION_TYPES).optional()
});

const uiBlockColumnSchema = z.object({
  key: z.string(),
  label: z.string(),
  type: z.enum(COLUMN_TYPES)
});

const metricSummaryBlockSchema = z.object({
  type: z.literal(UI_BLOCK_METRIC_SUMMARY),
  title: z.string().optional(),
  items: z.array(
    z.object({
      label: z.string(),
      value: z.string(),
      description: z.string().optional()
    })
  )
});

const insightCardBlockSchema = z.object({
  type: z.literal(UI_BLOCK_INSIGHT_CARD),
  title: z.string().optional(),
  content: z.string()
});

const suggestedActionsBlockSchema = z.object({
  type: z.literal(UI_BLOCK_SUGGESTED_ACTIONS),
  title: z.string().optional(),
  actions: z.array(
    z.object({
      label: z.string(),
      message: z.string()
    })
  )
});

const dataTableBlockSchema = z.object({
  type: z.literal(UI_BLOCK_DATA_TABLE),
  title: z.string().optional(),
  data: z.object({
    columns: z.array(uiBlockColumnSchema),
    rows: z.array(z.record(z.string(), z.unknown()))
  })
});

const uiBlockSchema = z.discriminatedUnion("type", [
  metricSummaryBlockSchema,
  insightCardBlockSchema,
  suggestedActionsBlockSchema,
  dataTableBlockSchema
]);

const uiBlocksParametersSchema = z.object({
  uiBlockId: z.string().optional(),
  blocks: z.array(uiBlockSchema)
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
      pageContext: DEFAULT_PAGE_CONTEXT,
      userContext: DEFAULT_USER_CONTEXT
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
      showDevConsole={false}
      onError={({ error, code, context }) => {
        onApplyError(new Error(`CopilotKit 请求失败：${code} ${error.message} ${JSON.stringify(context)}`));
      }}
    >
      <CopilotRuntimeContextBridge context={runtimeContext} />
      <ChartAgentProgressRenderer />
      <ChartAgentUiBlocksRenderer />
      <ChartAgentActionRenderer onApplyAction={onApplyAction} onApplyError={onApplyError} />
      <CopilotSidebar
        agentId={CHART_AGENT_ID}
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

function ChartAgentActionRenderer({
  onApplyAction,
  onApplyError
}: {
  onApplyAction: (action: ChartAgentAction) => void;
  onApplyError: (error: unknown) => void;
}) {
  const appliedActionIds = useRef(new Set<string>());
  const streamedAction = useLatestChartAgentAction();

  useEffect(() => {
    if (!streamedAction || appliedActionIds.current.has(streamedAction.actionId)) return;

    try {
      onApplyAction(streamedAction.action);
      appliedActionIds.current.add(streamedAction.actionId);
    } catch (error) {
      onApplyError(error);
      appliedActionIds.current.add(streamedAction.actionId);
    }
  }, [streamedAction, onApplyAction, onApplyError]);

  useRenderTool({
    name: CHART_AGENT_ACTION_TOOL,
    parameters: actionParametersSchema,
    render: ({ parameters, result }) => {
      const payload = readActionPayload(result);
      const actionId = payload?.actionId ?? parameters.actionId;
      const action = payload?.action ?? null;
      return (
        <ChartAgentActionApplier
          action={action}
          actionId={actionId}
          appliedActionIds={appliedActionIds.current}
          onApplyAction={onApplyAction}
          onApplyError={onApplyError}
        />
      );
    }
  });

  return null;
}

function ChartAgentActionApplier({
  action,
  actionId,
  appliedActionIds,
  onApplyAction,
  onApplyError
}: {
  action: ChartAgentAction | null;
  actionId: string | undefined;
  appliedActionIds: Set<string>;
  onApplyAction: (action: ChartAgentAction) => void;
  onApplyError: (error: unknown) => void;
}) {
  useEffect(() => {
    if (!action || !actionId || appliedActionIds.has(actionId)) return;

    try {
      onApplyAction(action);
      appliedActionIds.add(actionId);
    } catch (error) {
      onApplyError(error);
      appliedActionIds.add(actionId);
    }
  }, [action, actionId, appliedActionIds, onApplyAction, onApplyError]);

  return null;
}

function ChartAgentProgressRenderer() {
  useRenderTool({
    name: CHART_AGENT_PROGRESS_TOOL,
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

function ChartAgentUiBlocksRenderer() {
  useRenderTool({
    name: CHART_AGENT_UI_BLOCKS_TOOL,
    parameters: uiBlocksParametersSchema,
    render: ({ parameters, result }) => {
      const payload = readUiBlocksPayload(result);
      const blocks = payload?.blocks ?? parameters.blocks ?? [];
      const uiBlockId = payload?.uiBlockId ?? parameters.uiBlockId;
      return <ChatUiBlocks blocks={blocks} uiBlockId={uiBlockId} />;
    }
  });

  return null;
}

function ChatUiBlocks({ blocks, uiBlockId }: { blocks: ChartAgentUiBlock[]; uiBlockId: string | undefined }) {
  if (blocks.length === 0) return null;

  return (
    <section className="chat-ui-blocks" aria-label="生成式 UI" data-ui-block-id={uiBlockId}>
      {blocks.map((block, index) => (
        <ChatUiBlock block={block} key={`${block.type}-${index}`} />
      ))}
    </section>
  );
}

function ChatUiBlock({ block }: { block: ChartAgentUiBlock }) {
  if (block.type === UI_BLOCK_METRIC_SUMMARY) {
    return (
      <article className="chat-ui-card">
        <h3>{block.title ?? "指标摘要"}</h3>
        <dl className="chat-ui-summary-grid">
          {block.items.map((item) => (
            <div className="chat-ui-summary-item" key={`${item.label}-${item.value}`}>
              <dt>{item.label}</dt>
              <dd>{item.value}</dd>
              {item.description ? <p>{item.description}</p> : null}
            </div>
          ))}
        </dl>
      </article>
    );
  }

  if (block.type === UI_BLOCK_INSIGHT_CARD) {
    return (
      <article className="chat-ui-card">
        <h3>{block.title ?? "图表洞察"}</h3>
        <p className="chat-ui-insight">{block.content}</p>
      </article>
    );
  }

  if (block.type === UI_BLOCK_SUGGESTED_ACTIONS) {
    return (
      <article className="chat-ui-card">
        <h3>{block.title ?? "建议操作"}</h3>
        <div className="chat-ui-action-list">
          {block.actions.map((action) => (
            <button
              className="chat-ui-action-chip"
              key={`${action.label}-${action.message}`}
              onClick={() => submitCopilotChatMessage(action.message)}
              title={action.message}
              type="button"
            >
              {action.label}
            </button>
          ))}
        </div>
      </article>
    );
  }

  return (
    <article className="chat-ui-card">
      <h3>{block.title ?? "数据明细"}</h3>
      <div className="chat-ui-table-wrap">
        <table className="chat-ui-table">
          <thead>
            <tr>
              {block.data.columns.map((column) => (
                <th key={column.key}>{column.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {block.data.rows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {block.data.columns.map((column) => (
                  <td key={column.key}>{formatCellValue(row[column.key])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
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

function readActionPayload(result: unknown): { actionId?: string; action: ChartAgentAction | null } | null {
  if (!result) return null;

  const parsed = typeof result === "string" ? safeJsonParse(result) : result;
  if (!parsed || typeof parsed !== "object") return null;

  const value = parsed as Record<string, unknown>;
  const action = value.action;
  return {
    actionId: typeof value.actionId === "string" ? value.actionId : undefined,
    action: isChartAgentAction(action) ? action : null
  };
}

function readUiBlocksPayload(result: unknown): { uiBlockId?: string; blocks: ChartAgentUiBlock[] } | null {
  if (!result) return null;

  const parsed = typeof result === "string" ? safeJsonParse(result) : result;
  const validation = uiBlocksParametersSchema.safeParse(parsed);
  return validation.success ? (validation.data as { uiBlockId?: string; blocks: ChartAgentUiBlock[] }) : null;
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

function formatCellValue(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
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
