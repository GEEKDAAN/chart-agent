import { AbstractAgent } from "@ag-ui/client";
import type { BaseEvent, Message, RunAgentInput } from "@ag-ui/core";
import { Observable } from "rxjs";

import { progressSnapshot, progressSnapshots } from "./progress.js";
import {
  AGUI_RUN_ERROR_EVENT,
  AGUI_RUN_FINISHED_EVENT,
  AGUI_RUN_STARTED_EVENT,
  AGUI_TEXT_MESSAGE_CONTENT_EVENT,
  AGUI_TEXT_MESSAGE_END_EVENT,
  AGUI_TEXT_MESSAGE_START_EVENT,
  AGUI_TOOL_CALL_ARGS_EVENT,
  AGUI_TOOL_CALL_END_EVENT,
  AGUI_TOOL_CALL_RESULT_EVENT,
  AGUI_TOOL_CALL_START_EVENT,
  ACTION_CREATE_CHART,
  ACTION_ERROR,
  ACTION_UPDATE_CHART,
  CHART_AGENT_ACTION_TOOL,
  CHART_AGENT_BACKEND_CHAT_PATH,
  CHART_AGENT_CONTEXT_KEY,
  CHART_AGENT_CONTEXT_MARKER_PREFIX,
  CHART_AGENT_ID,
  CHART_AGENT_PROGRESS_TOOL,
  DEFAULT_BACKEND_URL,
  DEFAULT_PAGE_CONTEXT,
  DEFAULT_USER_CONTEXT,
  INTENT_CREATE_CHART
} from "./protocol.js";

type ChartAgentOptions = {
  backendUrl: string;
};

type ChartAgentResponse = {
  conversationId: string;
  intent: string;
  action: {
    type: typeof ACTION_CREATE_CHART | typeof ACTION_UPDATE_CHART | typeof ACTION_ERROR;
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
      agentId: CHART_AGENT_ID,
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
    let progressIntent = INTENT_CREATE_CHART;

    subscriber.next({
      type: AGUI_RUN_STARTED_EVENT,
      threadId: input.threadId,
      runId: input.runId,
      input
    } as BaseEvent);
    subscriber.next({ type: AGUI_TEXT_MESSAGE_START_EVENT, messageId, role: "assistant" } as BaseEvent);

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
        type: AGUI_TEXT_MESSAGE_CONTENT_EVENT,
        messageId,
        delta: formatChartAgentResponse(chartResponse),
        timestamp: 0
      } as BaseEvent);
      subscriber.next({ type: AGUI_TEXT_MESSAGE_END_EVENT, messageId, timestamp: 0 } as BaseEvent);
      subscriber.next({
        type: AGUI_RUN_FINISHED_EVENT,
        threadId: input.threadId,
        runId: input.runId
      } as BaseEvent);
      subscriber.complete();
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      if (progressToolStarted) {
        subscriber.next({
          type: AGUI_TOOL_CALL_RESULT_EVENT,
          messageId: `tool-result-${progressToolCallId}-failed`,
          toolCallId: progressToolCallId,
          content: JSON.stringify(progressSnapshot(progressIntent, progressToolCallId, 1, "failed")),
          role: "tool",
          timestamp: 0
        } as BaseEvent);
        subscriber.next({
          type: AGUI_TOOL_CALL_END_EVENT,
          toolCallId: progressToolCallId,
          timestamp: 0
        } as BaseEvent);
      }
      subscriber.next({
        type: AGUI_TEXT_MESSAGE_CONTENT_EVENT,
        messageId,
        delta: `处理失败：${message}`,
        timestamp: 0
      } as BaseEvent);
      subscriber.next({ type: AGUI_TEXT_MESSAGE_END_EVENT, messageId, timestamp: 0 } as BaseEvent);
      subscriber.next({
        type: AGUI_RUN_ERROR_EVENT,
        message,
        code: "chart_agent_error"
      } as BaseEvent);
      subscriber.complete();
    }
  }

  private async requestChartAgent(input: RunAgentInput, message: string, context: RuntimeContext): Promise<ChartAgentResponse> {
    const backendUrl = normalizeBackendUrl(process.env.CHART_AGENT_BACKEND_URL);
    const response = await fetch(`${backendUrl}${CHART_AGENT_BACKEND_CHAT_PATH}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        conversationId: input.threadId,
        message,
        currentChart: context.currentChart ?? null,
        pageContext: context.pageContext ?? DEFAULT_PAGE_CONTEXT,
        userContext: context.userContext ?? DEFAULT_USER_CONTEXT
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
    type: AGUI_TOOL_CALL_START_EVENT,
    toolCallId,
    toolCallName: CHART_AGENT_PROGRESS_TOOL,
    parentMessageId: messageId,
    rawEvent: { parameters: initialProgress },
    timestamp: 0
  } as BaseEvent);
  for (const snapshot of snapshots.slice(0, -1)) {
    subscriber.next({
      type: AGUI_TOOL_CALL_ARGS_EVENT,
      toolCallId,
      delta: JSON.stringify(snapshot),
      timestamp: 0
    } as BaseEvent);
  }
  subscriber.next({
    type: AGUI_TOOL_CALL_RESULT_EVENT,
    messageId: `tool-result-${toolCallId}-1`,
    toolCallId,
    content: JSON.stringify(snapshots.at(-1) ?? initialProgress),
    role: "tool",
    timestamp: 0
  } as BaseEvent);
  subscriber.next({
    type: AGUI_TOOL_CALL_END_EVENT,
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
    type: AGUI_TOOL_CALL_START_EVENT,
    toolCallId,
    toolCallName: CHART_AGENT_ACTION_TOOL,
    parentMessageId: messageId,
    rawEvent: { parameters: { actionId: toolCallId, actionType: response.action.type } },
    timestamp: 0
  } as BaseEvent);
  subscriber.next({
    type: AGUI_TOOL_CALL_RESULT_EVENT,
    messageId: `tool-result-${toolCallId}-1`,
    toolCallId,
    content: JSON.stringify({ actionId: toolCallId, action: response.action }),
    role: "tool",
    timestamp: 0
  } as BaseEvent);
  subscriber.next({
    type: AGUI_TOOL_CALL_END_EVENT,
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
  const chartAgentContext = isRecord(state[CHART_AGENT_CONTEXT_KEY]) ? state[CHART_AGENT_CONTEXT_KEY] : {};
  return { ...chartAgentContext, ...forwardedProps } as RuntimeContext;
}

function formatChartAgentResponse(response: ChartAgentResponse): string {
  return response.action.message;
}

function shouldEmitChartAction(response: ChartAgentResponse): boolean {
  return response.action.type === ACTION_CREATE_CHART || response.action.type === ACTION_UPDATE_CHART;
}

function stripContextMarker(content: string): string {
  const start = content.indexOf(CHART_AGENT_CONTEXT_MARKER_PREFIX);
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
    return DEFAULT_BACKEND_URL;
  }
  return value.replace(/\/$/, "");
}
