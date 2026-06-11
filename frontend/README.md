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
