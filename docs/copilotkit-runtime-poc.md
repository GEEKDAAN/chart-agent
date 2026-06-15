# CopilotKit 官方 Runtime SDK PoC 评估

## 结论

`0.11.0` 分支已验证官方 CopilotKit Runtime SDK 可以接管项目的 `/copilotkit` Runtime 入口，但实现形态需要新增一个 Node Runtime 服务：

```text
React + CopilotKit
  -> Node CopilotKit Runtime SDK
  -> FastAPI /chart-agent/chat
  -> LangGraph ChartAgent
  -> ChartAgentAction
  -> React 应用图表变更
```

原因是当前官方 Runtime SDK 主要提供 Node/Express/Hono 接入，未提供可直接嵌入 FastAPI 的 Python Runtime SDK。

## 已验证能力

- 官方 `@copilotkit/runtime/v2` + Express 可以提供 `/copilotkit/info`、`/copilotkit/agent/{agentId}/run` 等 Runtime 端点。
- 自定义 AG-UI `AbstractAgent` 可以承接 CopilotKit agent run，并调用现有 FastAPI 图表业务接口。
- 前端 `CopilotKitProvider`、`CopilotSidebar`、`useAgentContext`、`useRenderTool(chartAgentProgress)` 可以继续使用。
- 生成图表、修改图表类型、修改样式、新增指标、当前图表问答均已通过 Playwright E2E。
- 前端上下文仍通过请求补丁写入 `forwardedProps`，官方 Runtime 可以把该上下文传入自定义 Agent。

## 当前限制

- Runtime 服务从单 FastAPI 进程变成 `FastAPI + Node Runtime` 两个进程，部署和本地启动复杂度增加。
- `chartAgentProgress` 在 PoC 中由 Node Runtime 输出开始/完成快照，尚未恢复 `0.10.3` 的 LangGraph 节点级连续流转。
- 前端仍保留 `fetch patch` 注入上下文和监听 SSE 进度快照，官方 Runtime 没有直接消除这层过渡代码。
- 图表 action 仍通过隐藏 `chart-agent-action` marker 传回前端，后续可评估更标准的 AG-UI state/custom event 方式。

## 是否建议立即合并主线

不建议直接合并到 `main` 作为正式替换。

建议先把本分支作为 `0.11.0` PoC 验收分支，明确接受以下架构变化后，再规划 `0.12.0` 正式迁移：

- 接受新增 Node Runtime 服务。
- 接受部署层从两个服务变成三个服务：前端、Node Runtime、FastAPI。
- 补回 LangGraph 节点级进度流转。
- 给 Runtime 服务补单元测试或契约测试。

## 后续建议

如果继续推进官方 Runtime SDK：

1. 将 Node Runtime 的 `ChartAgent` 代理逻辑拆成更明确的 `agent`、`context`、`progress`、`action-marker` 模块。
2. 在 FastAPI 增加一个内部流式 endpoint，输出 LangGraph 节点进度，Node Runtime 转换为 `chartAgentProgress`。
3. 研究是否可以用 AG-UI `STATE_DELTA` 或 `CUSTOM` 事件替代隐藏 action marker。
4. 再决定是否删除前端 `fetch patch`，改用官方稳定上下文传递方式。
