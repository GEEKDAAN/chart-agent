import assert from "node:assert/strict";
import test, { type TestContext } from "node:test";

import type { BaseEvent, RunAgentInput } from "@ag-ui/core";

import { ChartAgent } from "../src/chart-agent.js";
import {
  ACTION_CREATE_CHART,
  ACTION_ERROR,
  ACTION_UPDATE_CHART,
  CHART_AGENT_ACTION_TOOL,
  CHART_AGENT_CONTEXT_KEY,
  CHART_AGENT_PROGRESS_TOOL,
  CHART_AGENT_UI_BLOCKS_TOOL
} from "../src/protocol.js";

type FetchCall = {
  url: string;
  body: Record<string, unknown>;
};

test("forwards current chart context and emits progress/action for chart creation", async (t) => {
  const fetchCalls: FetchCall[] = [];
  mockFetch(t, fetchCalls, {
    conversationId: "thread-1",
    intent: ACTION_CREATE_CHART,
    action: {
      type: ACTION_CREATE_CHART,
      message: "已生成图表",
      chart: { chartType: "bar", title: "销售额" },
      chartId: "chart-1"
    }
  });

  const events = await runAgent({
    threadId: "thread-1",
    runId: "run-1",
    messages: [{ id: "m1", role: "user", content: "近30天各销售渠道的销售额" }],
    forwardedProps: {
      currentChart: { chartType: "line", title: "旧图表" },
      pageContext: { source: "test-page" },
      userContext: { userId: "u1", tenantId: "t1" }
    }
  });

  assert.equal(fetchCalls.length, 1);
  assert.deepEqual(fetchCalls[0]?.body.currentChart, { chartType: "line", title: "旧图表" });
  assert.deepEqual(fetchCalls[0]?.body.pageContext, { source: "test-page" });
  assert.deepEqual(fetchCalls[0]?.body.userContext, { userId: "u1", tenantId: "t1" });

  assertToolStarted(events, CHART_AGENT_PROGRESS_TOOL);
  assertToolStarted(events, CHART_AGENT_ACTION_TOOL);
  const actionResult = parseToolResult(events, CHART_AGENT_ACTION_TOOL);
  assert.equal(actionResult.actionId.startsWith("action-"), true);
  assert.equal(actionResult.action.type, ACTION_CREATE_CHART);
  assert.equal(actionResult.action.message, "已生成图表");
});

test("uses state chartAgentContext when forwardedProps are absent", async (t) => {
  const fetchCalls: FetchCall[] = [];
  mockFetch(t, fetchCalls, {
    conversationId: "thread-2",
    intent: "update_style",
    action: {
      type: ACTION_UPDATE_CHART,
      message: "已更新样式",
      patch: { series: [{ name: "抖音", color: "#ef4444" }] }
    }
  });

  const events = await runAgent({
    threadId: "thread-2",
    runId: "run-2",
    messages: [{ id: "m1", role: "user", content: "把抖音改成红色" }],
    state: {
      [CHART_AGENT_CONTEXT_KEY]: {
        currentChart: { chartType: "bar", title: "渠道销售额" }
      }
    }
  });

  assert.deepEqual(fetchCalls[0]?.body.currentChart, { chartType: "bar", title: "渠道销售额" });
  assertToolStarted(events, CHART_AGENT_PROGRESS_TOOL);
  assertToolStarted(events, CHART_AGENT_ACTION_TOOL);
});

test("does not emit progress or action tools for current chart questions", async (t) => {
  const fetchCalls: FetchCall[] = [];
  mockFetch(t, fetchCalls, {
    conversationId: "thread-3",
    intent: "answer_current_chart_question",
    action: {
      type: ACTION_ERROR,
      message: "当前图表包含抖音、小红书、微信、天猫。"
    }
  });

  const events = await runAgent({
    threadId: "thread-3",
    runId: "run-3",
    messages: [{ id: "m1", role: "user", content: "有哪些渠道？" }],
    forwardedProps: {
      currentChart: { chartType: "bar", title: "渠道销售额" }
    }
  });

  assert.equal(fetchCalls.length, 1);
  assertNoToolStarted(events, CHART_AGENT_PROGRESS_TOOL);
  assertNoToolStarted(events, CHART_AGENT_ACTION_TOOL);
  assertTextContains(events, "当前图表包含抖音、小红书、微信、天猫。");
});

test("emits ui blocks tool event when backend returns generated ui blocks", async (t) => {
  const fetchCalls: FetchCall[] = [];
  mockFetch(t, fetchCalls, {
    conversationId: "thread-ui-blocks",
    intent: ACTION_CREATE_CHART,
    action: {
      type: ACTION_CREATE_CHART,
      message: "已生成图表。",
      chart: { chartType: "bar", title: "销售额" },
      chartId: "chart-ui-blocks"
    },
    uiBlocks: [
      {
        type: "insight_card",
        title: "主要洞察",
        content: "抖音渠道销售额最高。"
      }
    ]
  });

  const events = await runAgent({
    threadId: "thread-ui-blocks",
    runId: "run-ui-blocks",
    messages: [{ id: "m1", role: "user", content: "近30天各销售渠道的销售额" }]
  });

  assert.equal(fetchCalls.length, 1);
  assertToolStarted(events, CHART_AGENT_PROGRESS_TOOL);
  assertToolStarted(events, CHART_AGENT_ACTION_TOOL);
  assertToolStarted(events, CHART_AGENT_UI_BLOCKS_TOOL);
  const uiBlocksResult = parseToolResult(events, CHART_AGENT_UI_BLOCKS_TOOL);
  assert.equal(uiBlocksResult.uiBlockId.startsWith("ui-blocks-"), true);
  assert.deepEqual(uiBlocksResult.blocks, [
    {
      type: "insight_card",
      title: "主要洞察",
      content: "抖音渠道销售额最高。"
    }
  ]);
});

test("does not emit ui blocks tool event when backend returns empty ui blocks", async (t) => {
  const fetchCalls: FetchCall[] = [];
  mockFetch(t, fetchCalls, {
    conversationId: "thread-empty-ui-blocks",
    intent: ACTION_CREATE_CHART,
    action: {
      type: ACTION_CREATE_CHART,
      message: "已生成图表。",
      chart: { chartType: "bar", title: "销售额" },
      chartId: "chart-empty-ui-blocks"
    },
    uiBlocks: []
  });

  const events = await runAgent({
    threadId: "thread-empty-ui-blocks",
    runId: "run-empty-ui-blocks",
    messages: [{ id: "m1", role: "user", content: "近30天各销售渠道的销售额" }]
  });

  assert.equal(fetchCalls.length, 1);
  assertToolStarted(events, CHART_AGENT_PROGRESS_TOOL);
  assertToolStarted(events, CHART_AGENT_ACTION_TOOL);
  assertNoToolStarted(events, CHART_AGENT_UI_BLOCKS_TOOL);
});

test("returns readable error events when backend request fails", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response("backend failed", { status: 500 });

  try {
    const events = await runAgent({
      threadId: "thread-4",
      runId: "run-4",
      messages: [{ id: "m1", role: "user", content: "生成图表" }]
    });

    assert.equal(events.some((event) => event.type === "RUN_ERROR"), true);
    assertTextContains(events, "ChartAgent backend failed: 500");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

function mockFetch(t: TestContext, fetchCalls: FetchCall[], responseBody: Record<string, unknown>) {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (input, init) => {
    fetchCalls.push({
      url: String(input),
      body: JSON.parse(String(init?.body ?? "{}"))
    });
    return Response.json(responseBody);
  };
  t.after(() => {
    globalThis.fetch = originalFetch;
  });
}

function runAgent(input: Partial<RunAgentInput>): Promise<BaseEvent[]> {
  const agent = new ChartAgent({ backendUrl: "http://backend.test" });
  const events: BaseEvent[] = [];

  return new Promise((resolve, reject) => {
    agent.run(input as RunAgentInput).subscribe({
      next: (event) => events.push(event),
      error: reject,
      complete: () => resolve(events)
    });
  });
}

function assertToolStarted(events: BaseEvent[], toolName: string) {
  assert.equal(events.some((event) => event.type === "TOOL_CALL_START" && event.toolCallName === toolName), true);
}

function assertNoToolStarted(events: BaseEvent[], toolName: string) {
  assert.equal(events.some((event) => event.type === "TOOL_CALL_START" && event.toolCallName === toolName), false);
}

function assertTextContains(events: BaseEvent[], expected: string) {
  const text = events
    .filter((event) => event.type === "TEXT_MESSAGE_CONTENT")
    .map((event) => event.delta)
    .join("");
  assert.equal(text.includes(expected), true);
}

function parseToolResult(events: BaseEvent[], toolName: string): Record<string, any> {
  const start = events.find((event) => event.type === "TOOL_CALL_START" && event.toolCallName === toolName);
  assert.ok(start);
  const result = events.find((event) => event.type === "TOOL_CALL_RESULT" && event.toolCallId === start.toolCallId);
  assert.ok(result);
  return JSON.parse(String(result.content));
}
