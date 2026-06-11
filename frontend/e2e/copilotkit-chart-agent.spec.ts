import { expect, test } from "@playwright/test";

test("CopilotKit sidebar can generate and update a chart with structured steps", async ({ page }) => {
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

  await sendPrompt(page, "看最近30天各渠道销售额");
  await expect(page.locator("canvas")).toHaveCount(1);
  await expect(page.locator(".chat-progress")).toBeVisible();
  await expect(page.locator(".chat-progress")).toContainText("执行步骤");
  await expect(page.locator(".chat-progress")).toContainText("同步到前端");
  await expect(page.locator(".chat-progress")).toContainText("已完成");

  await sendPrompt(page, "换成折线图");
  await expect(page.locator(".chat-progress").last()).toContainText("运行 Agent Workflow");

  await sendPrompt(page, "把抖音改成红色");
  await sendPrompt(page, "加一列利润率");
  await sendPrompt(page, "解释一下这个图");

  const pageText = await page.locator("body").innerText();
  expect(pageText).toContain("执行步骤");
  expect(pageText).not.toContain("执行状态：");
  expect(pageText).not.toContain("chart-agent-action");
  expect(pageText).not.toContain("chart-agent-step");

  expect(agentRuns).toHaveLength(5);
  expect(agentRuns[0]).toMatchObject({
    prompt: "看最近30天各渠道销售额",
    hasCurrentChart: false,
    chartType: null
  });
  expect(agentRuns[1]).toMatchObject({
    prompt: "换成折线图",
    hasCurrentChart: true,
    chartType: "bar"
  });
  expect(agentRuns[2]).toMatchObject({
    prompt: "把抖音改成红色",
    hasCurrentChart: true,
    chartType: "line"
  });

  expect(badResponses).toEqual([]);
});

async function sendPrompt(page: import("@playwright/test").Page, prompt: string) {
  await page.locator("textarea").fill(prompt);
  await page.locator("button").last().click();
  await expect(page.getByText(prompt)).toBeVisible();
  await expect(page.locator(".chat-progress").last()).toContainText("解析用户需求");
}
