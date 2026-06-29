# 受控生成式 UI 设计

本文档定义 chart-agent 后续生成式 UI 的演进方向。当前项目已经具备自然语言图表生成、编辑、问答和 CopilotKit 工具渲染能力，但核心仍是图表 Agent，不是完整生成式 UI。

## 当前状态

当前链路是：

```text
用户自然语言
  -> CopilotKit 聊天入口
  -> Runtime 转发上下文
  -> FastAPI / LangGraph Agent 决策
  -> 返回 ChartAgentAction
  -> 前端校验并更新 ChartSpec
  -> ECharts 渲染图表
```

这套模式的优点是稳定、可控、容易测试。模型不会直接生成 React 组件、ECharts option 或 SQL，图表状态只通过受控 `ChartAgentAction` 更新。

它的限制是：UI 结构主要由前端预先固定，Agent 只能改变图表数据和样式，不能根据任务动态组合洞察卡片、摘要、建议操作和辅助明细。

## 目标形态

生成式 UI 的目标不是让 LLM 生成代码，而是让 Agent 根据任务动态生成结构化 UI 描述，再由前端白名单组件渲染。

目标链路是：

```text
用户自然语言
  -> CopilotKit 聊天入口
  -> Runtime 转发 currentChart / pageContext
  -> 后端 Agent 决策和数据查询
  -> 返回 ChartAgentAction + uiBlocks
  -> Runtime 转换为 CopilotKit 工具事件
  -> 前端 useRenderTool 渲染受控 UI Blocks
  -> ChartAgentAction 继续更新主图表状态
```

核心原则：

- `ChartAgentAction` 仍然是图表状态变更的唯一协议。
- `uiBlocks` 只负责展示增强，不直接修改图表状态。
- LLM 不允许直接返回 React 组件。
- LLM 不允许直接返回任意 ECharts option。
- 前端只渲染白名单 block type。
- 所有 block payload 必须有 schema 校验。

## UI Blocks

首批建议支持的 UI Block：

```ts
type ChartAgentUiBlock =
  | MetricSummaryBlock
  | InsightCardBlock
  | SuggestedActionsBlock
  | DataTableBlock;
```

语义说明：

- `metric_summary`：展示总览指标、最高值、最低值、同比/环比等轻量摘要。
- `insight_card`：展示图表洞察、异常提示、解释说明和分析结论。
- `suggested_actions`：展示建议操作，例如“隐藏天猫”“切换成折线图”“查看利润率”。
- `data_table`：展示当前图表数据的轻量明细视图。

后续可以扩展更多 block，但必须先补充前后端 schema、domain 常量、Runtime 工具事件测试和 E2E 验收场景。

## CopilotKit 职责

CopilotKit 在生成式 UI 中负责：

- 提供自然语言入口：`CopilotSidebar` 或 `CopilotChat`。
- 传递上下文：当前 `ChartSpec`、页面状态和用户上下文。
- 承载工具事件：`chartAgentProgress`、`chartAgentAction`、后续的 `chartAgentUiBlocks`。
- 通过 `useRenderTool` 把动态 UI Blocks 渲染到原生聊天消息中。

当前不改变以下边界：

- 不新增普通聊天框。
- 不注册业务型 `useFrontendTool` 来执行图表创建、修改或数据查询。
- 不让前端成为业务 Agent 的执行通道。

## 后端职责

后端 Agent 负责：

- 判断是否需要生成 UI Blocks。
- 基于当前图表、查询结果和用户意图生成结构化 `uiBlocks`。
- 校验 block type、payload 和数量限制。
- 在 LLM 不可用时使用 deterministic fallback 生成基础摘要。

后端不得：

- 生成 React 代码。
- 生成任意 HTML。
- 生成任意 ECharts option。
- 通过 `uiBlocks` 绕过 `ChartAgentAction` 修改图表状态。

## 前端职责

前端负责：

- 定义 UI Block TypeScript 类型和运行时校验。
- 注册白名单渲染组件。
- 通过 `useRenderTool(chartAgentUiBlocks)` 渲染 CopilotKit 消息内 UI。
- 对非法 block type 或非法 payload 做降级处理，不能让页面崩溃。
- suggested action 点击后仍然走自然语言请求链路，而不是直接修改图表。

## Runtime 职责

Runtime 负责：

- 接收 FastAPI 返回的 `uiBlocks`。
- 为每次 UI Blocks 输出生成稳定 `uiBlockId`。
- 转换为 CopilotKit / AG-UI 工具事件。
- 不解释业务语义，不修改 block payload。

## 协议方向

后续响应协议保持兼容扩展：

```ts
type ChartAgentResponse = {
  conversationId: string;
  intent: Intent;
  action: ChartAgentAction;
  uiBlocks?: ChartAgentUiBlock[];
};
```

后续 Runtime 工具事件：

```ts
type ChartAgentUiBlocksPayload = {
  uiBlockId: string;
  blocks: ChartAgentUiBlock[];
};
```

没有 `uiBlocks` 时，现有图表生成、编辑、问答行为必须保持不变。

## 首个验收场景

推荐第一个生成式 UI 场景：

```text
用户：近30天各渠道销售额
```

预期效果：

- 主图表仍按现有 `ChartAgentAction` 创建。
- CopilotKit 对话中出现一组受控 UI Blocks：
  - 指标摘要卡：总销售额、最高渠道、最低渠道。
  - 洞察卡：渠道差异或异常提示。
  - 建议操作：隐藏某渠道、切换趋势图、查看利润率。
- 点击建议操作后，将自然语言指令送回 CopilotKit 输入或请求链路，仍由后端 Agent 决策。

## 分阶段路线

1. `0.11.21`：写入生成式 UI 架构文档，不改业务代码。
2. `0.11.22`：新增 `uiBlocks` schema/type/domain 常量，默认不输出。
3. `0.11.23`：前端新增 UI Block renderer 和首批组件。
4. `0.11.24`：Runtime 新增 `chartAgentUiBlocks` 工具事件。
5. `0.11.25`：后端生成图表后返回首批洞察 UI Blocks。
6. 后续：接入真实 LLM 增强洞察文案，但必须保留 deterministic fallback。
