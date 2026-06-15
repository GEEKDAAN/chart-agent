# 前端

React + Vite 前端 MVP，负责维护 `ChartSpec`、调用后端图表 Agent、校验 action 并用 ECharts 渲染图表。

## CopilotKit

前端已接入 CopilotKit 侧边栏。配置 Runtime 地址后，CopilotKit 侧边栏是当前唯一的自然语言交互入口。

```bash
VITE_COPILOT_RUNTIME_URL=/copilotkit
VITE_BACKEND_PROXY_URL=http://localhost:8000
```

本地开发推荐使用相对路径 `/copilotkit`，由 Vite 将 `/copilotkit` 和 `/chart-agent` 统一代理到 `VITE_BACKEND_PROXY_URL`，避免浏览器跨域预检失败。

侧边栏请求会携带当前 `ChartSpec` 上下文到后端 Runtime。前端会同时通过 CopilotKit `properties`、readable context 和 Runtime 请求体补丁传递当前图表，避免不同 CopilotKit 请求结构下丢失上下文。

后端响应会附带不可见的 `ChartAgentAction` 标记，前端解析后复用现有 `applyChartAction` 自动刷新图表。

当前版本不再保留普通对话框 fallback，页面生成和编辑图表都通过 CopilotKit 侧边栏完成。

## 聊天内执行步骤

CopilotKit 聊天消息内会展示结构化执行步骤，用于说明当前 Agent 请求的处理进度。内容包含需求解析、图表上下文读取、数据需求规划、后端 workflow 运行、图表变更生成和前端同步。

步骤数据来自后端 Runtime 输出的 AG-UI tool call 事件，前端通过 CopilotKit `useRenderTool` 注册 `chartAgentProgress` 渲染器展示。当前实现不再维护主工作区外置步骤面板，也不再使用 `chart-agent-step` 隐藏 marker。

进度协议维护说明见根目录 `docs/progress-protocol.md`。

## 本地运行

```bash
cd frontend
npm install
npm run dev
```

如果 PowerShell 拦截 `npm.ps1`，可以使用：

```bash
npm.cmd install
npm.cmd run dev
```

## 端到端测试

前端新增 Playwright E2E 测试，用于验证 CopilotKit 侧边栏到后端 Runtime、图表生成、图表编辑和上下文传递的完整链路。

```bash
cd frontend
npm.cmd run test:e2e
```

默认端口：

```bash
E2E_FRONTEND_PORT=5178
E2E_BACKEND_PORT=8004
```

测试配置会自动启动或复用本地服务：

- 后端：`python -m uvicorn app.main:app --host 127.0.0.1 --port 8004`
- 前端：`npm.cmd run dev -- --host 127.0.0.1 --port 5178`

测试环境默认设置 `CHART_AGENT_LLM_MODE=off`，确保自动化测试走确定性规则链路，不依赖外部 LLM 服务。当前配置优先使用本机 Chrome；如果其他机器没有安装 Chrome，需要先安装 Playwright 浏览器或调整 `playwright.config.ts` 的浏览器配置。
