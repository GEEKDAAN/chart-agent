import { expect, test } from "@playwright/test";

test("CopilotKit sidebar can generate and update a chart with streamed structured steps", async ({ page }) => {
  const badResponses: { status: number; url: string }[] = [];
  const agentRuns: { prompt: string; hasCurrentChart: boolean; chartType: string | null }[] = [];

  page.on("response", (response) => {
    if (response.status() >= 400) {
      badResponses.push({ status: response.status(), url: response.url() });
    }
  });

  page.on("request", (request) => {
    if (!request.url().includes("/copilotkit") || request.method() !== "POST") return;

    const postData = request.postData();
    if (!postData) return;

    const payload = JSON.parse(postData);
    const body = payload.body ?? payload;
    const lastMessage = body.messages?.at(-1);
    if (lastMessage?.role !== "user") return;

    agentRuns.push({
      prompt: lastMessage.content,
      hasCurrentChart: Boolean(body.forwardedProps?.currentChart),
      chartType: body.forwardedProps?.currentChart?.chartType ?? null
    });
  });

  await page.goto("/");
  await expect(page.getByText("CopilotKit 已启用")).toBeVisible();
  await expect(page.locator(".workspace").getByText("执行步骤")).toHaveCount(0);
  await expect(page.locator("textarea")).toBeVisible();

  const createResult = await sendPrompt(page, "近30天各销售渠道的销售额");
  await expect(page.locator("canvas")).toHaveCount(1);
  await expect(page.locator(".chat-progress")).toBeVisible();
  await expect(page.locator(".chat-progress")).toContainText("执行步骤");
  await expect(page.locator(".chat-progress")).toContainText("识别图表需求");
  await expect(page.locator(".chat-progress")).toContainText("同步到前端");
  await expect(page.locator(".chat-progress")).toContainText("已完成");
  const uiBlocks = toolResultByName(createResult.events, "chartAgentUiBlocks");
  expect(uiBlocks?.blocks?.map((block: Record<string, unknown>) => block.type)).toEqual([
    "metric_summary",
    "insight_card",
    "suggested_actions"
  ]);
  await expect(page.locator(".chat-ui-blocks")).toBeVisible();
  await page.getByRole("button", { name: "查看渠道" }).click();
  await expect(page.getByText("有哪些渠道？").last()).toBeVisible();
  await expect(page.getByText(/抖音.*小红书.*微信.*天猫/).last()).toBeVisible();

  await sendPrompt(page, "换成折线图");
  await expect(page.locator(".chat-progress").last()).toContainText("识别图表类型");

  await sendPrompt(page, "把抖音改成红色");
  await expect(page.locator(".chat-progress").last()).toContainText("识别样式修改");

  await sendPrompt(page, "加一列利润率");
  await expect(page.locator(".chat-progress").last()).toContainText("识别数据修改");

  const progressCountBeforeQuestion = await page.locator(".chat-progress").count();
  await sendPrompt(page, "解释一下这个图", { expectProgress: false });
  await expect(page.locator(".chat-progress")).toHaveCount(progressCountBeforeQuestion);
  await sendPrompt(page, "有哪些渠道？", { expectProgress: false });
  await expect(page.getByText(/抖音.*小红书.*微信.*天猫/).last()).toBeVisible();
  await sendPrompt(page, "抖音的销售额有多少？", { expectProgress: false });
  await expect(page.getByText(/168,000/)).toBeVisible();

  const pageText = await page.locator("body").innerText();
  expect(pageText).toContain("执行步骤");
  expect(pageText).not.toContain("执行状态：");
  expect(pageText).not.toContain("chart-agent-action");
  expect(pageText).not.toContain("chart-agent-step");

  expect(agentRuns).toHaveLength(8);
  expect(agentRuns[0]).toMatchObject({
    prompt: "近30天各销售渠道的销售额",
    hasCurrentChart: false,
    chartType: null
  });
  expect(agentRuns[1]).toMatchObject({
    prompt: "有哪些渠道？",
    hasCurrentChart: true,
    chartType: "bar"
  });
  expect(agentRuns[2]).toMatchObject({
    prompt: "换成折线图",
    hasCurrentChart: true,
    chartType: "bar"
  });
  expect(agentRuns[3]).toMatchObject({
    prompt: "把抖音改成红色",
    hasCurrentChart: true,
    chartType: "line"
  });
  expect(agentRuns[5]).toMatchObject({
    prompt: "解释一下这个图",
    hasCurrentChart: true
  });
  expect(agentRuns[6]).toMatchObject({
    prompt: "有哪些渠道？",
    hasCurrentChart: true
  });
  expect(agentRuns[7]).toMatchObject({
    prompt: "抖音的销售额有多少？",
    hasCurrentChart: true
  });

  expect(badResponses).toEqual([]);
});

test("CopilotKit separates new chart requests from current chart questions", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("CopilotKit 已启用")).toBeVisible();
  await expect(page.locator("textarea")).toBeVisible();

  const trendResult = await sendPrompt(page, "最近30天的销售趋势");
  const trendAction = toolResultByName(trendResult.events, "chartAgentAction")?.action;
  expect(trendAction?.type).toBe("create_chart");
  expect(trendAction?.chart?.chartType).toBe("line");
  expect(trendAction?.chart?.encoding?.x).toBe("date");

  const channelResult = await sendPrompt(page, "给我展示近30天各渠道的销售额");
  const channelAction = toolResultByName(channelResult.events, "chartAgentAction")?.action;
  expect(channelAction?.type).toBe("create_chart");
  expect(channelAction?.chart?.chartType).toBe("bar");
  expect(channelAction?.chart?.encoding?.x).toBe("channel");
  expect(channelAction?.chart?.encoding?.y).toBe("sales");

  const progressCountBeforeQuestion = await page.locator(".chat-progress").count();
  const questionResult = await sendPrompt(page, "有哪些渠道？", { expectProgress: false });
  expect(toolResultByName(questionResult.events, "chartAgentAction")).toBeUndefined();
  expect(toolResultByName(questionResult.events, "chartAgentUiBlocks")).toBeUndefined();
  await expect(page.locator(".chat-progress")).toHaveCount(progressCountBeforeQuestion);
  await expect(page.getByText(/抖音.*小红书.*微信.*天猫/).last()).toBeVisible();
});

type SendPromptResult = {
  content: string;
  events: Record<string, any>[];
};

async function sendPrompt(
  page: import("@playwright/test").Page,
  prompt: string,
  options: { expectProgress?: boolean } = {}
): Promise<SendPromptResult> {
  const expectProgress = options.expectProgress ?? true;
  const progressCount = await page.locator(".chat-progress").count();
  const responsePromise = page.waitForResponse((response) => {
    if (!response.url().includes("/copilotkit") || response.request().method() !== "POST") return false;
    const postData = response.request().postData();
    if (!postData) return false;

    try {
      const payload = JSON.parse(postData);
      const body = payload.body ?? payload;
      const lastMessage = body.messages?.at(-1);
      return lastMessage?.role === "user" && lastMessage.content === prompt;
    } catch {
      return false;
    }
  });

  await page.locator("textarea").fill(prompt);
  await page.locator("button").last().click();
  await expect(page.getByText(prompt).last()).toBeVisible();
  const response = await responsePromise;
  const content = await response.text();
  const events = readSseEvents(content);
  const toolStartNames = events
    .filter((event) => event.type === "TOOL_CALL_START")
    .map((event) => event.toolCallName);

  if (expectProgress) {
    expect(toolStartNames).toContain("chartAgentProgress");
    expect(toolStartNames).toContain("chartAgentAction");
    expect(content).toContain('\\"sequence\\":');
    await expect(page.locator(".chat-progress").last()).toContainText("识别");
    await expect(page.locator(".chat-progress").last()).toContainText("已完成", { timeout: 12_000 });
  } else {
    expect(toolStartNames).not.toContain("chartAgentProgress");
    expect(toolStartNames).not.toContain("chartAgentAction");
    await expect(page.locator(".chat-progress")).toHaveCount(progressCount);
  }

  return { content, events };
}

function readSseEvents(content: string): Record<string, any>[] {
  return content
    .split("\n\n")
    .map((block) =>
      block
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trim())
        .join("\n")
    )
    .filter(Boolean)
    .map((value) => {
      try {
        return JSON.parse(value);
      } catch {
        return null;
      }
    })
    .filter((value): value is Record<string, any> => Boolean(value && typeof value === "object"));
}

function toolResultByName(events: Record<string, any>[], toolName: string): Record<string, any> | undefined {
  const toolCallIds = new Set(
    events
      .filter((event) => event.type === "TOOL_CALL_START" && event.toolCallName === toolName)
      .map((event) => event.toolCallId)
  );
  const result = events.find((event) => event.type === "TOOL_CALL_RESULT" && toolCallIds.has(event.toolCallId));
  if (!result || typeof result.content !== "string") return undefined;

  try {
    return JSON.parse(result.content);
  } catch {
    return undefined;
  }
}
