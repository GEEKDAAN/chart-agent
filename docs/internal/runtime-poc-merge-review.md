# CopilotKit Runtime PoC 合并前审查

## 审查结论

`codex/copilotkit-runtime-poc` 分支已经具备进入主线评估的基础条件，但不建议直接按“生产完成态”理解。

当前实现适合作为下一阶段主线基础：它已经把 CopilotKit 官方 Runtime SDK、前端 CopilotKit 组件、后端 FastAPI 图表 Agent 串成了可验收链路；同时仍存在几个明确的过渡实现，需要在后续版本继续收敛。

建议结论：

- 可以作为候选分支继续推进合并评估。
- 合并前需要接受三服务架构：`Vite + Node Runtime + FastAPI`。
- 合并后需要优先处理上下文传递兜底、真实流式进度、部署说明三类问题。

## 当前架构

```text
用户输入
  -> React / CopilotSidebar
  -> CopilotKitProvider
  -> Node CopilotKit Runtime SDK (/copilotkit)
  -> FastAPI /chart-agent/chat
  -> LangGraph ChartAgent
  -> ChartAgentAction
  -> Node Runtime 输出 AG-UI 工具事件
  -> useRenderTool 渲染步骤面板并应用图表动作
```

## 已确认能力

- 前端使用 `CopilotKitProvider` 连接 Runtime。
- 前端使用 `CopilotSidebar` 提供官方聊天 UI。
- 前端使用 `useAgentContext` 暴露当前图表上下文和前端指令。
- 前端使用 `useRenderTool(chartAgentProgress)` 在聊天消息内渲染结构化步骤面板。
- 前端使用 `useRenderTool(chartAgentAction)` 接收并应用图表动作。
- Node Runtime 使用官方 `@copilotkit/runtime/v2` 和 Express 暴露 `/copilotkit`。
- Node Runtime 使用自定义 AG-UI `AbstractAgent` 转发请求到 FastAPI。
- FastAPI 继续负责 LLM-first 决策、LangGraph 编排、数据查询、图表 action 生成和校验。
- 当前图表问答不会触发步骤面板或图表动作。
- 本地脚本已支持三服务一键启动和停止。
- 自动化测试覆盖了 Runtime 契约、后端核心路径、前端 E2E 和中文编码检查。

## 主要风险

### R1：上下文传递仍有前端 patch 兜底

当前前端同时使用 `useAgentContext` 和 `CopilotKitProvider properties`，但为了确保 Runtime 请求一定携带 `currentChart`，仍保留了 `window.fetch` patch。

影响：

- 可维护性弱于纯官方 API 接入。
- CopilotKit 请求格式变化时，patch 逻辑可能失效。
- 需要用 E2E 和 Runtime 契约测试持续保护。

建议：

- 短期保留，因为它解决了当前最关键的上下文稳定性问题。
- 后续单独开任务验证是否可以完全依赖官方上下文传递能力。
- 移除前必须保留“生成图后连续追问当前图表信息”的 E2E 覆盖。

### R2：步骤面板不是后端节点实时流

当前 FastAPI `/chart-agent/chat` 是非流式 JSON 接口。Runtime 拿到最终结果后，根据 intent 合成多步骤快照，再通过 AG-UI 工具事件发给前端。

影响：

- 用户能看到结构化步骤流转，但它不是 LangGraph 节点真实执行进度。
- 如果后端某一步耗时较长，前端无法实时显示该节点已经开始或卡住。
- 排障信息仍主要依赖后端日志。

建议：

- 短期接受该实现，作为 UI 交互过渡版本。
- 后续新增 FastAPI 内部流式接口，由 LangGraph 节点事件驱动 Runtime 输出 `chartAgentProgress`。
- 真正接入流式前，文档中必须明确当前是“Runtime 合成进度”。

### R3：三服务架构增加部署和排障复杂度

项目从原来的 `Vite + FastAPI` 变成 `Vite + Node Runtime + FastAPI`。

影响：

- 本地开发、端口配置、日志定位更复杂。
- 生产部署需要新增 Node Runtime 服务。
- Runtime 与 FastAPI 之间需要内部网络、健康检查和错误处理策略。

建议：

- 保留 `scripts/dev.ps1` 和 `scripts/stop-dev.ps1` 作为本地标准入口。
- 合并主线前补充生产部署拓扑。
- 后续为 Runtime 增加 `/health` 到 FastAPI 的依赖健康检查，而不只是返回自身状态。

### R4：Runtime 对后端响应结构依赖较强

Runtime 假设 FastAPI 返回稳定的 `ChartAgentResponse`，并根据 `intent` 判断是否渲染步骤，根据 `action.type` 判断是否应用图表动作。

影响：

- 后端协议变更会直接影响 CopilotKit 工具事件。
- 如果 intent 命名变化，步骤面板可能消失或显示错误模板。

建议：

- 保留并扩展 Runtime 契约测试。
- 将 `intent -> progress template` 的映射视为正式协议的一部分。
- 后续在 `docs/progress-protocol.md` 中继续维护该协议。

### R5：真实大模型模式仍可能出现非确定性

本地自动化测试默认使用 `CHART_AGENT_LLM_MODE=off`，真实 LLM 模式依赖外部模型服务质量、延迟和结构化输出稳定性。

影响：

- off 模式通过不等于真实模型全通过。
- 模型误判意图时，可能影响连续问答体验。

建议：

- 保留 off 模式作为基础回归测试。
- 真实 LLM 模式增加人工验收清单。
- 后续补充少量可选的 LLM smoke test，但不要让 CI 强依赖外部模型。

## 合并前验收标准

合并主线前建议至少满足：

1. `runtime` 单元测试通过。
2. `backend` 单元测试通过。
3. `frontend` 构建通过。
4. `frontend` E2E 通过。
5. 中文编码检查通过。
6. 本地三服务能用统一脚本启动。
7. 页面可完成以下连续链路：
   - 生成“近30天各销售渠道的销售额”。
   - 追问“有哪些渠道？”。
   - 追问“抖音的销售额有多少？”。
   - 修改“把抖音改成红色”。
   - 切换“换成折线图”。
8. 当前图表问答不新增步骤面板。
9. 生成和修改类请求必须出现步骤面板。
10. assistant 文本中不出现隐藏 action marker。

## 合并建议

建议分两步处理：

1. 当前分支继续作为 Runtime 主线候选分支，先不急于合并。
2. 完成一次最终三服务验收后，再合并回 `main`。

合并后优先级建议：

1. 收敛 CopilotKit 上下文传递，评估移除 `fetch` patch。
2. 设计 FastAPI 到 Runtime 的真实流式进度协议。
3. 补充生产部署说明和健康检查。
4. 扩展真实 LLM 模式下的人工验收清单。
