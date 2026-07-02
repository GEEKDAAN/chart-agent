# 代码质量评估

本文档记录当前 `chart-agent` 的代码质量状态、主要风险和建议治理顺序。评估基于当前 `main` 分支的代码结构、测试覆盖和近期生成式 UI 改造结果。

## 总体结论

当前代码质量适合公开展示和继续迭代，核心架构边界基本清晰：

- 前端、Runtime、后端三服务职责明确。
- 后端 Agent 拥有最终业务决策权。
- 图表状态变更收敛到 `ChartAgentAction`。
- 生成式 UI 收敛到白名单 `uiBlocks`。
- 常量和协议治理已经明显优于早期魔法字符串堆叠。
- 后端、Runtime、前端构建和 E2E 都有基础验证。

但当前还不应视为生产级代码。主要问题不是“能不能跑”，而是后续功能继续增加时，部分聚合文件会快速变重。

## 优点

### 架构边界清楚

`frontend/`、`runtime/`、`backend/` 的职责划分明确。前端不直接执行业务 Agent 工具，Runtime 专注 CopilotKit 协议适配，后端负责意图决策、数据查询和 action 生成。

### 协议受控

`ChartAgentAction`、`ChartSpec`、`ChartPatch`、`uiBlocks` 都是受控结构。前端在应用 action 前做校验，降低了模型输出直接污染渲染层的风险。

### 测试基础较完整

当前已有：

- 后端 API、workflow、数据需求、LLM 决策和 UI Blocks 测试。
- Runtime 契约测试。
- 前端 build 验证。
- Playwright E2E 覆盖 CopilotKit、Runtime、后端和图表渲染链路。

### 文档治理较好

`AGENTS.md`、工程规范、测试规范、架构文档、生成式 UI 设计和公开 README 已经能支撑外部读者理解项目。

## 主要风险

### 后端 Agent 已完成初步拆分

`0.11.32` 已将 `backend/app/agents/chart_agent_graph.py` 拆分为更清晰的边界：

- LangGraph 编排。
- `backend/app/agents/chart_agent_nodes.py`：节点实现、路由判断、查询节点和响应节点。
- `backend/app/services/chart_actions.py`：创建图表、更新样式、更新数据、切换图表类型和图表问答 action 构造。
- `backend/app/services/action_errors.py`：错误 action 和节点错误状态辅助。

当前 graph 入口已明显变轻，符合“agent 编排 workflow，service 承载业务逻辑”的边界。后续继续增加工具和图表类型时，建议进一步拆分 action 服务内部职责：

- `chart_updates.py`
- `chart_explanations.py`
- `chart_type_updates.py`
- `chart_action_messages.py`

`0.11.33` 已将 `ChartAgentState` 和 `DataRequirements` 迁移到 `backend/app/schemas/agent_state.py`，避免 service 层继续依赖 `agents/` 包内类型。

### 前端 CopilotKit 面板已完成初步拆分

`0.11.31` 已将 `frontend/src/components/CopilotKitPanel.tsx` 中的主要职责拆分到 `frontend/src/components/copilot/`，包括：

- CopilotKit Provider。
- Runtime context bridge。
- action 工具渲染。
- progress 工具渲染。
- uiBlocks 工具渲染。
- UI Block 组件。
- schema 校验。

当前面板入口已明显变轻。后续仍可继续细化：

- 将 `ui-blocks/ChatUiBlocks.tsx` 继续拆成 `MetricSummaryBlock`、`InsightCardBlock`、`DataTableBlock` 和 `SuggestedActionsBlock`。
- 为 CopilotKit 工具 payload 解析补更细的前端单元测试。
- 将建议操作发送适配逻辑纳入更稳定的 E2E helper。

### E2E 存在轻微时序抖动

合并前验证中，E2E 第一次出现过 `waitForResponse` 超时，重跑通过。当前判断不是业务回归，但说明测试对 CopilotKit 请求时序较敏感。

建议后续优化：

- 优先等待用户消息发送结果和 UI 状态变化。
- 减少对单个 `/copilotkit` response 捕获时机的依赖。
- 为建议操作点击和普通输入发送分别封装更稳的 helper。

### 真实数据源尚未接入

当前 mock 指标服务适合验证架构，但离生产仍缺：

- 指标目录配置。
- 权限和租户校验。
- 数据源适配器。
- 查询超时、限流和审计。
- 真实数据返回 schema 校验。

## 优先治理顺序

1. 继续细化 `chart_actions.py`，将样式更新、图表解释和类型切换拆成更小 service。
2. 继续细化前端 `ui-blocks/ChatUiBlocks.tsx` 的组件边界。
3. 优化 E2E `sendPrompt` helper，降低时序抖动。
4. 抽象真实数据源适配器接口。
5. 增加 CI，在项目更完善后自动运行单测、构建、文本检查和关键 E2E。

## 当前质量评级

以公开展示项目为标准：良好。

以长期可维护原型为标准：合格偏上。

以生产级产品为标准：仍需补齐真实数据源、权限、部署、监控、错误治理和更稳定的自动化测试。
