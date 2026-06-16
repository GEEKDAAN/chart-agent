# CopilotKit 官方 Runtime SDK PoC 评估

## 结论

`codex/copilotkit-runtime-poc` 分支已验证官方 CopilotKit Runtime SDK 可以接管项目的 `/copilotkit` Runtime 入口。

当前架构为：

```text
React + CopilotKit
  -> Node CopilotKit Runtime SDK
  -> FastAPI /chart-agent/chat
  -> LangGraph ChartAgent
  -> ChartAgentAction
  -> React 应用图表变更
```

采用 Node Runtime 的原因是：当前官方 Runtime SDK 主要提供 Node/Express/Hono 接入，未提供可直接嵌入 FastAPI 的 Python Runtime SDK。

## 已验证能力

- 官方 `@copilotkit/runtime/v2` + Express 可以提供 `/copilotkit` Runtime 端点。
- 自定义 AG-UI `AbstractAgent` 可以承接 CopilotKit agent run，并调用现有 FastAPI 图表业务接口。
- 前端 `CopilotKitProvider`、`CopilotSidebar`、`useAgentContext`、`useRenderTool` 可以继续使用。
- 生成图表、修改图表类型、修改样式、新增指标、当前图表问答均已通过 Playwright E2E。
- `chartAgentProgress` 已恢复为多步骤结构化快照，而不是单纯开始/完成两帧。
- `chartAgentAction` 已替代隐藏 `chart-agent-action` marker，用工具事件传递图表动作。
- 当前图表问答、闲聊、帮助和边界提示不会触发步骤卡或图表动作。
- 一键启动脚本已覆盖 FastAPI、Node Runtime、Vite 三服务本地启动。

## 当前限制

- Runtime 服务从单 FastAPI 进程变成 `FastAPI + Node Runtime` 两个后端进程，部署和本地排障复杂度增加。
- 前端仍保留 `fetch patch` 注入上下文和监听 SSE 工具结果，官方 Runtime 暂未完全消除这层过渡代码。
- FastAPI `/chart-agent/chat` 当前仍是非流式 JSON 接口，Runtime 基于最终结果输出步骤快照，不是后端节点实时流。
- Node Runtime 目前主要依赖 E2E 覆盖，后续仍建议补充更细的契约测试。

## 是否建议合并主线

建议在完成 `0.11.3` 本地开发脚本和文档收敛后，将该分支作为候选主线评估。

合并前需要确认：

- 接受新增 Node Runtime 服务。
- 接受部署层从两个服务变成三个服务：前端、Node Runtime、FastAPI。
- 接受当前前端请求补丁和 SSE 观察逻辑作为过渡实现。
- 后续计划补充 Runtime 契约测试和部署说明。

## 后续建议

1. 给 Runtime 服务补充单元测试或协议契约测试。
2. 评估是否能移除前端 `fetch patch`，完全依赖官方上下文传递能力。
3. 评估 FastAPI 是否需要新增内部流式 endpoint，由 Runtime 转换为真正实时的 `chartAgentProgress`。
4. 在决定合回 `main` 前，补充部署拓扑和生产环境启动方式。
