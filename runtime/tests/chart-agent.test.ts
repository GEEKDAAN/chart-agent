import assert from "node:assert/strict";
import test, { type TestContext } from "node:test";

import type { BaseEvent, RunAgentInput } from "@ag-ui/core";

import { ChartAgent } from "../src/chart-agent.js";

type FetchCall = {
  url: string;
  body: Record<string, unknown>;
};

test("forwards current chart context and emits progress/action for chart creation", async (t) => {
  const fetchCalls: FetchCall[] = [];
  mockFetch(t, fetchCalls, {
    conversationId: "thread-1",
    intent: "create_chart",
    action: {
      type: "create_chart",
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

  assertToolStarted(events, "chartAgentProgress");
  assertToolStarted(events, "chartAgentAction");
  const actionResult = parseToolResult(events, "chartAgentAction");
  assert.equal(actionResult.actionId.startsWith("action-"), true);
  assert.equal(actionResult.action.type, "create_chart");
  assert.equal(actionResult.action.message, "已生成图表");
});

test("uses state chartAgentContext when forwardedProps are absent", async (t) => {
  const fetchCalls: FetchCall[] = [];
  mockFetch(t, fetchCalls, {
    conversationId: "thread-2",
    intent: "update_style",
    action: {
      type: "update_chart",
      message: "已更新样式",
      patch: { series: [{ name: "抖音", color: "#ef4444" }] }
    }
  });

  const events = await runAgent({
    threadId: "thread-2",
    runId: "run-2",
    messages: [{ id: "m1", role: "user", content: "把抖音改成红色" }],
    state: {
      chartAgentContext: {
        currentChart: { chartType: "bar", title: "渠道销售额" }
      }
    }
  });

  assert.deepEqual(fetchCalls[0]?.body.currentChart, { chartType: "bar", title: "渠道销售额" });
  assertToolStarted(events, "chartAgentProgress");
  assertToolStarted(events, "chartAgentAction");
});

test("does not emit progress or action tools for current chart questions", async (t) => {
  const fetchCalls: FetchCall[] = [];
  mockFetch(t, fetchCalls, {
    conversationId: "thread-3",
    intent: "answer_current_chart_question",
    action: {
      type: "error",
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
  assertNoToolStarted(events, "chartAgentProgress");
  assertNoToolStarted(events, "chartAgentAction");
  assertTextContains(events, "当前图表包含抖音、小红书、微信、天猫。");
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
