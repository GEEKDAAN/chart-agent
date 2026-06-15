import { AbstractAgent } from "@ag-ui/client";
import type { BaseEvent, Message, RunAgentInput } from "@ag-ui/core";
import { Observable } from "rxjs";

import { progressSnapshot, progressSnapshots } from "./progress.js";

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

export class ChartAgent extends AbstractAgent {
  constructor({ backendUrl }: ChartAgentOptions) {
    super({
      agentId: "chart-agent",
      description: "Generate and edit validated ChartSpec charts."
    });
    process.env.CHART_AGENT_BACKEND_URL = normalizeBackendUrl(backendUrl);
  }

  run(input: RunAgentInput): Observable<BaseEvent> {
    return new Observable<BaseEvent>((subscriber) => {
      void this.runChartAgent(input, subscriber);
    });
  }

  private async runChartAgent(
    input: RunAgentInput,
    subscriber: { next: (event: BaseEvent) => void; error: (error: unknown) => void; complete: () => void }
  ) {
    const messageId = `msg-${crypto.randomUUID()}`;
    const progressToolCallId = `progress-${crypto.randomUUID()}`;
    const actionToolCallId = `action-${crypto.randomUUID()}`;
    let progressToolStarted = false;
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
      const chartResponse = await this.requestChartAgent(input, message, context);
      progressIntent = chartResponse.intent;

      emitProgressEvents(subscriber, messageId, progressToolCallId, chartResponse.intent, () => {
        progressToolStarted = true;
      });
      emitActionEvent(subscriber, messageId, actionToolCallId, chartResponse);

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
      if (progressToolStarted) {
        subscriber.next({
          type: "TOOL_CALL_RESULT",
          messageId: `tool-result-${progressToolCallId}-failed`,
          toolCallId: progressToolCallId,
          content: JSON.stringify(progressSnapshot(progressIntent, progressToolCallId, 1, "failed")),
          role: "tool",
          timestamp: 0
        } as BaseEvent);
        subscriber.next({
          type: "TOOL_CALL_END",
          toolCallId: progressToolCallId,
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

function emitProgressEvents(
  subscriber: { next: (event: BaseEvent) => void },
  messageId: string,
  toolCallId: string,
  intent: string,
  onStarted: () => void
) {
  const snapshots = progressSnapshots(intent, toolCallId, "completed");
  if (snapshots.length === 0) return;

  const [initialProgress] = snapshots;
  onStarted();
  subscriber.next({
    type: "TOOL_CALL_START",
    toolCallId,
    toolCallName: "chartAgentProgress",
    parentMessageId: messageId,
    rawEvent: { parameters: initialProgress },
    timestamp: 0
  } as BaseEvent);
  for (const snapshot of snapshots.slice(0, -1)) {
    subscriber.next({
      type: "TOOL_CALL_ARGS",
      toolCallId,
      delta: JSON.stringify(snapshot),
      timestamp: 0
    } as BaseEvent);
  }
  subscriber.next({
    type: "TOOL_CALL_RESULT",
    messageId: `tool-result-${toolCallId}-1`,
    toolCallId,
    content: JSON.stringify(snapshots.at(-1) ?? initialProgress),
    role: "tool",
    timestamp: 0
  } as BaseEvent);
  subscriber.next({
    type: "TOOL_CALL_END",
    toolCallId,
    timestamp: 0
  } as BaseEvent);
}

function emitActionEvent(
  subscriber: { next: (event: BaseEvent) => void },
  messageId: string,
  toolCallId: string,
  response: ChartAgentResponse
) {
  if (!shouldEmitChartAction(response)) return;

  subscriber.next({
    type: "TOOL_CALL_START",
    toolCallId,
    toolCallName: "chartAgentAction",
    parentMessageId: messageId,
    rawEvent: { parameters: { actionId: toolCallId, actionType: response.action.type } },
    timestamp: 0
  } as BaseEvent);
  subscriber.next({
    type: "TOOL_CALL_RESULT",
    messageId: `tool-result-${toolCallId}-1`,
    toolCallId,
    content: JSON.stringify({ actionId: toolCallId, action: response.action }),
    role: "tool",
    timestamp: 0
  } as BaseEvent);
  subscriber.next({
    type: "TOOL_CALL_END",
    toolCallId,
    timestamp: 0
  } as BaseEvent);
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

function formatChartAgentResponse(response: ChartAgentResponse): string {
  return response.action.message;
}

function shouldEmitChartAction(response: ChartAgentResponse): boolean {
  return response.action.type === "create_chart" || response.action.type === "update_chart";
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
