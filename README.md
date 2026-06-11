# chart-agent

图表解析 Agent，根据用户意图生成和编辑目标图表 UI。

项目目标是实现一个对话式图表生成与编辑系统：用户用自然语言表达分析意图，后端返回受控的 `ChartSpec` / `ChartPatch` / `ChartAgentAction`，前端校验后转换为 ECharts option 并渲染。

## 核心原则

- 模型只生成受控协议，不直接生成 React 组件。
- 模型不直接生成任意 ECharts option。
- Agent 不直接写 SQL，只能通过受控指标工具查询数据。
- 前端负责 `ChartSpec` 校验、patch 合并、ECharts option 转换和渲染。
- 每轮请求都携带当前 `chartSpec`，用于支持“把这个改成红色”这类上下文指令。

## 技术栈

- React + Vite
- ECharts
- FastAPI
- LangGraph
- OpenAI API（可选）
- CopilotKit（前端侧边栏和 Runtime 兼容端点）
- Python 语义指标层

## 目录结构

```text
backend/   FastAPI 接口、协议模型、LangGraph workflow、mock 指标查询
frontend/  React 应用、CopilotKit 侧边栏、ChartSpec runtime 和 ECharts 渲染
docs/      架构说明和设计文档
```

## 本地运行

后端：

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

如果 PowerShell 拦截 `npm.ps1`，使用：

```bash
npm.cmd install
npm.cmd run dev
```

CopilotKit 本地联调：

```bash
# 后端：建议用独立端口启动当前代码，避免和已有 8000 进程冲突
cd backend
set CHART_AGENT_LLM_MODE=off
uvicorn app.main:app --reload --port 8002

# 前端：在 frontend/.env 中配置相对 Runtime 地址和后端代理地址
VITE_COPILOT_RUNTIME_URL=/copilotkit
VITE_BACKEND_PROXY_URL=http://localhost:8002
```

说明：

- `CHART_AGENT_LLM_MODE=off` 用于稳定验证本地链路，避免外部 LLM 网络或额度影响联调。
- `frontend/.env` 和 `backend/.env` 只用于本地配置，已被 `.gitignore` 忽略，不能提交真实密钥。
- 页面状态显示 `CopilotKit 已启用` 时，表示前端已读取到 Runtime 地址。
- 当前前端不再提供普通对话框 fallback，图表生成和编辑都通过 CopilotKit 侧边栏完成。

访问：

```text
http://localhost:5173
```

## MVP 范围

- 单图表生成
- 单图表编辑
- 受控 `ChartSpec` 协议
- mock 指标目录和 mock 查询服务
- 可替换的后端指标服务层和 mock 数据源
- 确定性数据需求解析，支持指标、维度、筛选和简单时间范围
- LangGraph 单 Agent workflow
- 可选真实 LLM 结构化 action 生成
- CopilotKit 前端侧边栏
- CopilotKit Runtime 最小兼容端点
- CopilotKit 图表 action 自动应用
- CopilotKit 聊天内结构化执行步骤渲染
- 非流式 JSON 响应

## 暂不包含

- 多图 dashboard
- 图表持久化和分享
- 复杂下钻
- 多图联动
- CopilotKit 流式响应
- Agent 直接写 SQL

## 更新日志

项目变更记录在 `CHANGELOG.md` 中。新增版本记录时，请遵循其中定义的中文模块分组格式。

## 自动化测试

前端端到端测试使用 Playwright 维护，覆盖 CopilotKit 侧边栏、Runtime REST 请求、图表生成编辑和上下文传递链路。

```bash
cd frontend
npm.cmd run test:e2e
```

测试默认会自动启动或复用 `127.0.0.1:8004` 后端和 `127.0.0.1:5178` 前端服务，并以 `CHART_AGENT_LLM_MODE=off` 运行，避免外部 LLM 影响本地验证稳定性。
