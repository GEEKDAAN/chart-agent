# 前端

React + Vite 前端 MVP，负责维护 `ChartSpec`、调用后端图表 Agent、校验 action 并用 ECharts 渲染图表。

## CopilotKit

前端已接入可选 CopilotKit 侧边栏。默认不启用；配置 Runtime 地址后才会加载侧边栏代码。

```bash
VITE_COPILOT_RUNTIME_URL=http://localhost:8000/copilotkit
```

侧边栏请求会携带当前 `ChartSpec` 上下文到后端 Runtime。当前版本后端会返回 assistant 文本响应，用于打通 CopilotKit 到 `ChartAgent` 的链路；图表自动应用仍以后续前端 action 集成为准。

当前普通输入框仍然是稳定 fallback。

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
