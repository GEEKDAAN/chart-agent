# CopilotKit Runtime PoC

本目录是 `0.11.0` 官方 CopilotKit Runtime SDK PoC。

它使用 `@copilotkit/runtime/v2` + Express 提供 `/copilotkit` Runtime 端点，并把业务请求代理到 FastAPI `/chart-agent/chat`。

## 本地运行

```bash
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

## 职责边界

- Node Runtime：CopilotKit 官方 Runtime endpoint、AG-UI agent、`chartAgentProgress` 工具事件。
- FastAPI：图表业务 Agent、LLM-first 决策、数据查询、`ChartAgentAction` 生成和校验。
- React：CopilotKit UI、上下文注入、进度渲染、action marker 解析和图表应用。

## 当前限制

PoC 已验证主链路可行，但还没有恢复 LangGraph 节点级进度流转。当前步骤卡主要是开始/完成快照。
