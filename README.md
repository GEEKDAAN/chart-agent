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
- CopilotKit（可选前端侧边栏和 Runtime 兼容端点）
- Python 语义指标层

## 目录结构

```text
backend/   FastAPI 接口、协议模型、LangGraph workflow、mock 指标查询
frontend/  React 应用、ChartSpec runtime、ECharts 渲染和对话输入
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

访问：

```text
http://localhost:5173
```

## MVP 范围

- 单图表生成
- 单图表编辑
- 受控 `ChartSpec` 协议
- mock 指标目录和 mock 查询服务
- LangGraph 单 Agent workflow
- 可选真实 LLM 结构化 action 生成
- 可选 CopilotKit 前端侧边栏
- CopilotKit Runtime 最小兼容端点
- 非流式 JSON 响应
- 简单对话输入框

## 暂不包含

- 多图 dashboard
- 图表持久化和分享
- 复杂下钻
- 多图联动
- CopilotKit 前端 action 自动应用图表变更
- CopilotKit 流式响应
- Agent 直接写 SQL

## 更新日志

项目变更记录在 `CHANGELOG.md` 中。新增版本记录时，请遵循其中定义的中文模块分组格式。
