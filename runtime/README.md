# CopilotKit Runtime

本目录是官方 CopilotKit Runtime SDK 服务。

它使用 `@copilotkit/runtime/v2` + Express 提供 `/copilotkit` Runtime 端点，并把业务请求代理到 FastAPI `/chart-agent/chat`。

## 本地运行

推荐从项目根目录统一启动：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1
```

只启动 Runtime 时：

```powershell
cd runtime
npm.cmd install
set PORT=8014
set CHART_AGENT_BACKEND_URL=http://127.0.0.1:8004
npm.cmd run dev
```

健康检查：

```text
http://127.0.0.1:8014/health
```

## 测试

Runtime 契约测试使用 Node test runner，通过 mock FastAPI 响应验证 CopilotKit/AG-UI 事件输出：

```powershell
cd runtime
npm.cmd run test
```

## 职责边界

- Node Runtime：CopilotKit 官方 Runtime endpoint、AG-UI agent、工具事件编排。
- FastAPI：图表业务 Agent、LLM-first 决策、数据查询、`ChartAgentAction` 生成和校验。
- React：CopilotKit UI、上下文注入、步骤渲染、图表动作应用。

## 工具事件

Runtime 输出两个业务工具事件：

- `chartAgentProgress`：执行步骤面板。
- `chartAgentAction`：图表创建和修改动作。

assistant 文本只保留自然语言回复，不再携带隐藏 `chart-agent-action` marker。

## 当前限制

- Runtime 仍作为独立 Node 服务运行，部署时需要和 FastAPI 一起编排。
- 前端仍保留请求补丁和 SSE 观察逻辑，用于增强上下文传递和快速应用动作。
- 后端业务接口当前仍是非流式 JSON，Runtime 基于后端最终结果输出结构化步骤快照。
