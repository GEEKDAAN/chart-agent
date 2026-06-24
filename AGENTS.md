# AGENTS.md

本文档是 chart-agent 项目的协作规则入口，适用于人类开发者和 AI Agent。详细工程规范放在 `docs/`，本文档只保留必须长期遵守的项目边界和硬规则。

## 项目协作原则

- 项目文档、更新日志、提交信息默认使用中文。
- 代码命名、类型名、函数名和文件名默认使用英文；用户可见文案默认使用中文。
- 未经用户明确验收，不提交代码。
- 每个已验收版本必须更新 `CHANGELOG.md`。
- 不提交真实密钥、本地日志、临时文件、构建产物和测试产物。
- 修改前先阅读相关代码、测试和规范文档，优先沿用项目已有模式。

## 架构边界

- `frontend/`：React + Vite + ECharts + CopilotKit UI，负责图表展示、受控 action 应用和用户交互。
- `runtime/`：Node + 官方 CopilotKit Runtime SDK，负责 `/copilotkit` 协议入口、上下文转发和 AG-UI 工具事件。
- `backend/`：FastAPI + LangGraph，负责意图决策、数据需求解析、指标查询、图表 action 生成和校验。
- CopilotKit 负责聊天 UI、上下文传递和工具渲染。
- 后端 Agent 拥有最终业务决策权；LLM 决策必须经过后端校验。
- 前端只应用后端返回的受控 `ChartAgentAction`，不执行业务型 Agent 工具。

## 开发流程

1. 先判断需求属于新功能、修复、重构、文档还是工程治理。
2. 修改前读取相关模块、协议和测试。
3. 新增能力必须先补对应测试或决策矩阵用例。
4. 保持外部协议兼容；需要破坏性变更时必须明确说明并升级版本规则。
5. 完成后说明测试方式、测试结果、存在问题、原因和建议。
6. 用户验收通过后再提交。

## 魔法值与枚举管理

- 禁止在业务逻辑中新增未集中管理的字符串枚举或魔法值。
- `Intent`、`ToolName`、`ChartType`、`ActionType`、`MetricKey`、`DimensionKey`、颜色名、颜色值、progress step id 必须集中定义。
- 后端领域常量入口应收敛到 `backend/app/domain/`。
- 前端图表常量入口应收敛到 `frontend/src/domain/` 或现有 `frontend/src/lib/` 下的专用常量文件。
- schema 中的 `Literal` 可以保留，但业务判断应引用集中常量，避免重复硬编码。
- 新增枚举值时必须同步更新 schema、常量定义、决策矩阵测试、API/workflow 测试和 `CHANGELOG.md`。

## 后端规范入口

详见 [docs/backend-engineering-guidelines.md](docs/backend-engineering-guidelines.md)。

关键规则：

- router 只处理 HTTP 入参出参。
- agent 只编排 LangGraph workflow。
- service 负责具体业务逻辑。
- schema 是外部协议的唯一结构定义来源。
- LLM 可以优先参与语义判断，但后端 guardrail 必须拥有最终裁决权。

## 前端规范入口

详见 [docs/frontend-engineering-guidelines.md](docs/frontend-engineering-guidelines.md)。

关键规则：

- 不新增普通聊天框，统一使用 CopilotKit 前端组件作为自然语言入口。
- 不注册业务型 `useFrontendTool`，除非架构决策明确变更。
- `ChartSpec` 是前端图表渲染的唯一数据源。
- ECharts option 必须由受控 `ChartSpec` 派生。

## 测试规范入口

详见 [docs/testing-guidelines.md](docs/testing-guidelines.md)。

最低要求：

- 后端改动：运行 `python -m pytest -q`。
- Runtime 改动：运行 `npm.cmd run test` 和 `npm.cmd run build`。
- 前端改动：运行 `npm.cmd run build`。
- CopilotKit、上下文传递或关键交互改动：运行 Playwright E2E。
- 中文文案、文档或测试大量变更：运行 `runtime` 的 `npm.cmd run check:text`。
