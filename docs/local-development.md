# 本地开发与三服务说明

`chart-agent` 当前官方 CopilotKit Runtime 分支采用三服务本地架构：

```text
React + Vite
  -> Node CopilotKit Runtime (/copilotkit)
  -> FastAPI (/chart-agent/chat)
  -> LangGraph ChartAgent
```

## 服务职责

### FastAPI

FastAPI 是图表业务 Agent 后端，默认端口为 `8004`。

职责：

- 接收 `message + currentChart + pageContext + userContext`。
- 执行 LangGraph 图表 Agent。
- 进行 LLM-first 意图决策和后端校验。
- 查询 mock 指标数据。
- 生成并校验 `ChartAgentAction`。
- 回答当前图表问题。

主要接口：

```text
POST /chart-agent/chat
GET /health
```

### Node Runtime

Node Runtime 是 CopilotKit 官方 Runtime SDK 适配层，默认端口为 `8014`。

职责：

- 提供 `/copilotkit` Runtime 入口。
- 接收 CopilotKit 前端请求。
- 读取 CopilotKit 传入的当前图表上下文。
- 调用 FastAPI `/chart-agent/chat`。
- 输出 AG-UI / CopilotKit 工具事件：
  - `chartAgentProgress`：渲染步骤面板。
  - `chartAgentAction`：传递图表创建和修改动作。
- 输出 assistant 自然语言回复。

### Vite

Vite 是 React 前端开发服务，默认端口为 `5184`。

职责：

- 渲染图表工作区。
- 渲染 CopilotKit 侧边栏。
- 通过 `CopilotKitProvider` 连接 Runtime。
- 通过 `useRenderTool(chartAgentProgress)` 展示执行步骤。
- 通过 `useRenderTool(chartAgentAction)` 接收图表动作。
- 将当前 `ChartSpec` 上下文传给 Runtime。

## 一键启动

推荐用脚本统一启动三服务：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1
```

默认配置：

```text
LLM mode: off
Frontend: http://127.0.0.1:5184
Backend:  http://127.0.0.1:8004
Runtime:  http://127.0.0.1:8014/copilotkit
Logs:     tmp/
```

使用真实大模型模式：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1 -LlmMode openai
```

真实大模型模式会读取 `backend/.env` 中的配置，例如：

```text
CHART_AGENT_LLM_MODE=openai
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.5
OPENAI_BASE_URL=https://ai.allrealai.com/v1
```

`backend/.env` 已被 `.gitignore` 忽略，不应提交真实密钥。

## 停止服务

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop-dev.ps1
```

脚本会读取 `tmp/dev-processes.json`，按进程树停止三服务。

## 自定义端口

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1 `
  -BackendPort 8005 `
  -RuntimePort 8015 `
  -FrontendPort 5185
```

## 日志

启动脚本会写入：

```text
tmp/dev-backend.log
tmp/dev-runtime.log
tmp/dev-frontend.log
tmp/dev-backend.cmd
tmp/dev-runtime.cmd
tmp/dev-frontend.cmd
tmp/dev-processes.json
```

`tmp/` 是本地运行产物，不进入版本库。

## 验收路径

建议按以下顺序验证：

```text
近30天各销售渠道的销售额
换成折线图
把抖音改成红色
加一列利润率
有哪些渠道？
抖音的销售额有多少？
```

预期：

- 生成和修改类请求显示步骤面板。
- 当前图表问答不新增步骤面板。
- 图表动作通过 `chartAgentAction` 工具事件应用。
- 聊天文本不出现 `chart-agent-action` 隐藏 marker。
