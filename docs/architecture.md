# chart-agent 架构说明

## 概览

`chart-agent` 是一个对话式图表生成与编辑系统。用户通过自然语言表达分析意图，后端 Agent 负责决策、查询受控指标服务并返回结构化图表动作，前端校验后转换为 ECharts option 进行渲染。

项目刻意避免让模型直接生成可执行 UI、任意 ECharts option 或 SQL。所有模型输出都必须收敛到稳定协议，并由后端和前端分别校验。

## 主要模块

- **frontend**：React 应用，负责页面状态、当前 `ChartSpec`、图表渲染、CopilotKit 前端组件和受控 UI Blocks 渲染。
- **runtime**：Node Runtime 服务，基于官方 CopilotKit Runtime SDK 暴露 `/copilotkit` 入口，负责上下文转发和 AG-UI 工具事件。
- **backend**：FastAPI 服务，承接图表 Agent 请求，返回 `ChartAgentResponse`。
- **LangGraph ChartAgent**：编排意图决策、数据需求解析、指标查询、图表 action 生成和校验。
- **指标服务**：当前为 mock 指标目录和 mock 查询服务，后续可替换为真实指标平台或数据服务。
- **ECharts**：只消费前端根据受控 `ChartSpec` 派生出的 option。

## 数据流

```text
用户消息
  -> CopilotKit UI
  -> Node Runtime /copilotkit
  -> FastAPI /chart-agent/chat
  -> LangGraph ChartAgent
  -> 指标目录 / mock 查询服务
  -> ChartAgentAction + uiBlocks
  -> 后端校验
  -> Runtime 工具事件
  -> 前端 action 校验和应用
  -> ChartSpec 转 ECharts option
  -> 图表与生成式 UI 渲染
```

## 后端 Agent 流程

```text
decide_tool
  -> plan_data_if_needed
  -> query_metrics_if_needed
  -> generate_chart_action
  -> validate_chart_action
  -> build_ui_blocks_if_needed
  -> respond
```

`decide_tool` 采用 LLM-first 决策：优先让大模型基于用户消息和当前图表上下文输出结构化决策；后端再校验工具名、参数和置信度。LLM 不可用、低置信度或非法输出时，走确定性 fallback。

## 协议边界

后端返回的图表动作只允许使用受控 `ChartAgentAction`：

- `create_chart`
- `update_chart`
- `error`

前端只在校验通过后应用 action。`ChartPatch` 必须比 `Partial<ChartSpec>` 更窄，不能允许未知字段或图表 ID 被任意修改。

生成式 UI 使用 `uiBlocks`：

- `metric_summary`
- `insight_card`
- `data_table`
- `suggested_actions`

`uiBlocks` 只负责展示，不负责修改图表状态。建议操作点击后仍回到自然语言请求链路，由后端 Agent 再次决策。

## CopilotKit 的作用

项目当前使用 CopilotKit 的能力包括：

- `CopilotKitProvider`：接入 CopilotKit 前端上下文。
- `CopilotSidebar`：作为统一自然语言入口。
- `useAgentContext`：把当前图表、页面上下文和用户上下文传给 Runtime。
- `useRenderTool(chartAgentProgress)`：在聊天消息中渲染执行步骤。
- `useRenderTool(chartAgentUiBlocks)`：在聊天消息中渲染受控生成式 UI。
- Runtime SDK：提供 `/copilotkit` 协议入口，并向前端发送工具事件。

项目不使用业务型 `useFrontendTool` 执行图表创建或修改，避免形成前后端双执行通道。

## 生产风险

- 指标目录设计过弱会导致查询不稳定或语义歧义。
- 图表 patch 范围过宽会破坏图表状态。
- 前端缺少校验会让非法模型输出进入渲染层。
- 如果每轮请求不携带当前图表，上下文问答和连续编辑会失效。
- 当前指标查询仍是 mock 服务，接入真实数据源时需要补充权限、审计、限流和错误治理。
- Runtime 目前基于最终结果输出步骤事件，不是后端节点级实时流。
