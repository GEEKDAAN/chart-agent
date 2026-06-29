# 前端

React + Vite 前端负责维护 `ChartSpec`、渲染 ECharts 图表，并通过 CopilotKit 侧边栏承接自然语言交互。

## CopilotKit

当前唯一自然语言入口是 CopilotKit 侧边栏。

推荐从项目根目录统一启动：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1
```

Vite 代理配置：

```text
VITE_COPILOT_RUNTIME_URL=/copilotkit
VITE_BACKEND_PROXY_URL=http://127.0.0.1:8004
VITE_COPILOT_RUNTIME_PROXY_URL=http://127.0.0.1:8014
```

请求会携带当前 `ChartSpec` 上下文到 Node Runtime，再由 Node Runtime 转发给 FastAPI。

## 工具渲染

前端注册了三个 CopilotKit 工具渲染器：

- `chartAgentProgress`：在 CopilotKit 原生聊天消息中渲染结构化步骤面板。
- `chartAgentAction`：接收图表创建和修改动作，并调用 `applyChartAction` 更新图表。
- `chartAgentUiBlocks`：在聊天消息中渲染受控生成式 UI，包括指标摘要、洞察、数据明细和建议操作。

为了避免连续请求时当前图表上下文慢一拍，前端还会镜像监听 Runtime SSE 中的 `chartAgentAction` 工具结果，并通过 `actionId` 去重。

当前实现不再使用 `chart-agent-step` 或 `chart-agent-action` 隐藏 marker。

建议操作点击后仍然会发送自然语言请求，继续走 CopilotKit -> Runtime -> FastAPI Agent 链路，不在前端直接执行业务动作。

## 本地运行

只运行前端：

```powershell
cd frontend
npm.cmd install
npm.cmd run dev -- --host 127.0.0.1 --port 5184
```

完整联调请使用根目录脚本：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1
```

## 端到端测试

```powershell
cd frontend
npm.cmd run test:e2e
```

E2E 会自动启动或复用本地服务：

- FastAPI：`python -m uvicorn app.main:app --host 127.0.0.1 --port <E2E_BACKEND_PORT>`
- Node Runtime：`npm.cmd run dev`
- Vite：`npm.cmd run dev -- --host 127.0.0.1 --port <E2E_FRONTEND_PORT>`

测试环境默认设置 `CHART_AGENT_LLM_MODE=off`，避免外部 LLM 服务影响稳定性。
