import { AbstractAgent } from "@ag-ui/client";
import type { BaseEvent, Message, RunAgentInput } from "@ag-ui/core";
import { Observable } from "rxjs";

import { progressSnapshot, shouldRenderProgress } from "./progress.js";

type ChartAgentOptions = {
  backendUrl: string;
};

type ChartAgentResponse = {
  conversationId: string;
  intent: string;
  action: {
    type: "create_chart" | "update_chart" | "error";
    message: string;
    chart?: unknown;
    chartId?: string;
    patch?: unknown;
    code?: string;
  };
};

type RuntimeContext = {
  currentChart?: unknown;
  pageContext?: Record<string, unknown>;
  userContext?: {
    userId: string;
    tenantId: string;
  };
};

const nonFailureCodes = new Set(["explanation", "smalltalk", "help", "out_of_scope", "clarification_required"]);

export class ChartAgent extends AbstractAgent {
  constructor({ backendUrl }: ChartAgentOptions) {
    super({
      agentId: "chart-agent",
      description: "生成和编辑受控 ChartSpec 图表。"
    });
    process.env.CHART_AGENT_BACKEND_URL = normalizeBackendUrl(backendUrl);
  }

  run(input: RunAgentInput): Observable<BaseEvent> {
    return new Observable<BaseEvent>((subscriber) => {
      void this.runChartAgent(input, subscriber);
    });
  }

  private async runChartAgent(input: RunAgentInput, subscriber: { next: (event: BaseEvent) => void; error: (error: unknown) => void; complete: () => void }) {
    const messageId = `msg-${crypto.randomUUID()}`;
    const toolCallId = `tool-${crypto.randomUUID()}`;
    let toolCallStarted = false;
    let progressIntent = "create_chart";

    subscriber.next({
      type: "RUN_STARTED",
      threadId: input.threadId,
      runId: input.runId,
      input
    } as BaseEvent);
    subscriber.next({ type: "TEXT_MESSAGE_START", messageId, role: "assistant" } as BaseEvent);

    try {
      const message = lastUserMessage(input.messages);
      if (!message) {
        throw new Error("CopilotKit agent/run request does not contain a user text message");
      }

      const context = resolveRuntimeContext(input);
      progressIntent = previewProgressIntent(message, Boolean(context.currentChart));
      if (shouldRenderProgress(progressIntent)) {
        const initialProgress = progressSnapshot(progressIntent, toolCallId, 0, "running");
        toolCallStarted = true;
        subscriber.next({
          type: "TOOL_CALL_START",
          toolCallId,
          toolCallName: "chartAgentProgress",
          parentMessageId: messageId,
          rawEvent: { parameters: initialProgress },
          timestamp: 0
        } as BaseEvent);
        subscriber.next({
          type: "TOOL_CALL_ARGS",
          toolCallId,
          delta: JSON.stringify(initialProgress),
          timestamp: 0
        } as BaseEvent);
      }

      const chartResponse = await this.requestChartAgent(input, message, context);
      const shouldRender = shouldRenderProgress(chartResponse.intent);
      if (shouldRender) {
        subscriber.next({
          type: "TOOL_CALL_RESULT",
          messageId: `tool-result-${toolCallId}-1`,
          toolCallId,
          content: JSON.stringify(progressSnapshot(chartResponse.intent, toolCallId, 1, "completed")),
          role: "tool",
          timestamp: 0
        } as BaseEvent);
        subscriber.next({
          type: "TOOL_CALL_END",
          toolCallId,
          timestamp: 0
        } as BaseEvent);
      }

      subscriber.next({
        type: "TEXT_MESSAGE_CONTENT",
        messageId,
        delta: formatChartAgentResponse(chartResponse),
        timestamp: 0
      } as BaseEvent);
      subscriber.next({ type: "TEXT_MESSAGE_END", messageId, timestamp: 0 } as BaseEvent);
      subscriber.next({
        type: "RUN_FINISHED",
        threadId: input.threadId,
        runId: input.runId
      } as BaseEvent);
      subscriber.complete();
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      if (toolCallStarted) {
        subscriber.next({
          type: "TOOL_CALL_RESULT",
          messageId: `tool-result-${toolCallId}-failed`,
          toolCallId,
          content: JSON.stringify(progressSnapshot(progressIntent, toolCallId, 1, "failed")),
          role: "tool",
          timestamp: 0
        } as BaseEvent);
        subscriber.next({
          type: "TOOL_CALL_END",
          toolCallId,
          timestamp: 0
        } as BaseEvent);
      }
      subscriber.next({
        type: "TEXT_MESSAGE_CONTENT",
        messageId,
        delta: `处理失败：${message}`,
        timestamp: 0
      } as BaseEvent);
      subscriber.next({ type: "TEXT_MESSAGE_END", messageId, timestamp: 0 } as BaseEvent);
      subscriber.next({
        type: "RUN_ERROR",
        message,
        code: "chart_agent_error"
      } as BaseEvent);
      subscriber.complete();
    }
  }

  private async requestChartAgent(input: RunAgentInput, message: string, context: RuntimeContext): Promise<ChartAgentResponse> {
    const backendUrl = normalizeBackendUrl(process.env.CHART_AGENT_BACKEND_URL);
    const response = await fetch(`${backendUrl}/chart-agent/chat`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        conversationId: input.threadId,
        message,
        currentChart: context.currentChart ?? null,
        pageContext: context.pageContext ?? { source: "copilotkit-official-runtime-poc" },
        userContext: context.userContext ?? { userId: "copilotkit_user", tenantId: "demo" }
      })
    });

    if (!response.ok) {
      throw new Error(`ChartAgent backend failed: ${response.status}`);
    }
    return (await response.json()) as ChartAgentResponse;
  }
}

function lastUserMessage(messages: Message[] | undefined): string {
  for (const message of [...(messages ?? [])].reverse()) {
    if (message.role !== "user") continue;
    if (typeof message.content === "string") return stripContextMarker(message.content).trim();
    if (Array.isArray(message.content)) {
      return stripContextMarker(
        message.content
          .map((part) => (typeof part === "object" && part && "text" in part ? String(part.text) : ""))
          .join("")
      ).trim();
    }
  }
  return "";
}

function resolveRuntimeContext(input: RunAgentInput): RuntimeContext {
  const forwardedProps = isRecord(input.forwardedProps) ? input.forwardedProps : {};
  const state = isRecord(input.state) ? input.state : {};
  const chartAgentContext = isRecord(state.chartAgentContext) ? state.chartAgentContext : {};
  return { ...chartAgentContext, ...forwardedProps } as RuntimeContext;
}

function previewProgressIntent(message: string, hasCurrentChart: boolean): string {
  if (/换成|改成.*图|折线图|柱状图|饼图|表格/.test(message)) return "change_chart_type";
  if (/颜色|红色|蓝色|绿色|样式/.test(message)) return "update_style";
  if (/加一列|新增|利润率|指标/.test(message)) return "update_data";
  if (hasCurrentChart && /哪些|多少|解释|说明|这个图|图表/.test(message)) return "answer_current_chart_question";
  if (/你好|您好|hello|hi/i.test(message)) return "smalltalk";
  return "create_chart";
}

function formatChartAgentResponse(response: ChartAgentResponse): string {
  const action = response.action;
  if (action.type === "error") {
    return action.message;
  }

  return `${action.message}\n\n当前版本已通过 CopilotKit 官方 Runtime SDK PoC 调用后端图表 Agent。\n\n<!-- chart-agent-action:${encodeMarker(action)} -->`;
}

function encodeMarker(value: unknown): string {
  return Buffer.from(JSON.stringify(value), "utf8").toString("base64");
}

function stripContextMarker(content: string): string {
  const prefix = "<!-- chart-agent-context:";
  const start = content.indexOf(prefix);
  if (start < 0) return content;
  const end = content.indexOf(" -->", start);
  if (end < 0) return content.slice(0, start);
  return `${content.slice(0, start)}${content.slice(end + 4)}`.trim();
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function normalizeBackendUrl(value: string | undefined): string {
  if (!value || value === "undefined" || value === "null") {
    return "http://127.0.0.1:8000";
  }
  return value.replace(/\/$/, "");
}
