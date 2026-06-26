# chart-agent

`chart-agent` 是一个对话式图表生成与编辑项目。用户用自然语言描述分析需求，后端 Agent 返回受控的 `ChartSpec`、`ChartPatch` 或 `ChartAgentAction`，前端校验后转换为 ECharts option 并渲染。

## 核心原则

- 模型只生成受控协议，不直接生成 React 组件。
- 模型不直接生成任意 ECharts option。
- Agent 不直接写 SQL，只能通过受控指标工具查询数据。
- 前端负责 `ChartSpec` 校验、patch 合并、ECharts option 转换和渲染。
- 每轮请求都携带当前 `ChartSpec`，支持“把这个改成红色”这类上下文指令。

## 技术栈

- React + Vite
- ECharts
- FastAPI
- LangGraph
- OpenAI API 兼容接口，可选
- CopilotKit 前端侧边栏
- CopilotKit 官方 Runtime SDK，Node Runtime 服务
- Python 语义指标层

## 目录结构

```text
backend/   FastAPI 图表业务接口、协议模型、LangGraph workflow、mock 指标查询
runtime/   CopilotKit 官方 Runtime SDK 服务，负责 /copilotkit 入口
frontend/  React 应用、CopilotKit 侧边栏、ChartSpec runtime、ECharts 渲染
docs/      架构说明和设计文档
scripts/   本地三服务启动和停止脚本
```

## 工程规范

协作入口见 [AGENTS.md](AGENTS.md)。详细规范：

- [后端工程规范](docs/backend-engineering-guidelines.md)
- [前端工程规范](docs/frontend-engineering-guidelines.md)
- [测试规范](docs/testing-guidelines.md)

## 本地开发

当前官方 CopilotKit Runtime 分支需要同时运行三个服务：

- FastAPI：图表业务 Agent 后端。
- Node Runtime：CopilotKit 官方 Runtime 协议适配层。
- Vite：React 前端开发服务。

推荐使用统一脚本启动：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1
```

默认使用 `CHART_AGENT_LLM_MODE=off`，适合稳定验收本地链路。

使用真实大模型模式：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1 -LlmMode openai
```

停止服务：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop-dev.ps1
```

默认访问地址：

```text
http://127.0.0.1:5184
```

详细说明见 [docs/local-development.md](docs/local-development.md)。

CopilotKit 官方 Runtime SDK PoC 的合并前审查见 [docs/runtime-poc-merge-review.md](docs/runtime-poc-merge-review.md)。

Runtime PoC 合并回主线前的操作清单见 [docs/main-merge-checklist.md](docs/main-merge-checklist.md)。

## 环境变量

后端本地配置放在 `backend/.env`，该文件已被 `.gitignore` 忽略。

```text
CHART_AGENT_LLM_MODE=off
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.5
OPENAI_BASE_URL=https://ai.allrealai.com/v1
```

`CHART_AGENT_LLM_MODE=off` 用于稳定验证本地链路，避免外部 LLM 网络或额度影响联调。

## 当前能力

- 单图表生成
- 单图表编辑
- 受控 `ChartSpec` 协议
- mock 指标目录和 mock 查询服务
- 确定性数据需求解析
- LangGraph 单 Agent workflow
- 可选真实 LLM 结构化 action 生成
- CopilotKit 前端侧边栏
- CopilotKit 官方 Runtime SDK
- `chartAgentProgress` 聊天内步骤面板
- `chartAgentAction` 工具事件自动应用图表动作
- 当前图表问答

## 暂不包含

- 多图 dashboard
- 图表持久化和分享
- 复杂下钻
- 多图联动
- FastAPI 原生 CopilotKit Runtime
- Agent 直接写 SQL

## 自动化测试

前端端到端测试使用 Playwright，覆盖 CopilotKit 侧边栏、Runtime 请求、图表生成编辑和上下文传递链路。

```powershell
cd frontend
npm.cmd run test:e2e
```

测试默认以 `CHART_AGENT_LLM_MODE=off` 运行，避免外部 LLM 影响本地验证稳定性。

Runtime 契约测试覆盖 CopilotKit/AG-UI 工具事件和后端代理协议：

```powershell
cd runtime
npm.cmd run test
```

中文文案编码检查用于防止源码、测试和文档中再次出现乱码：

```powershell
cd runtime
npm.cmd run check:text
```

## 更新日志

项目变更记录在 [CHANGELOG.md](CHANGELOG.md)。新增版本记录时请遵循其中定义的中文模块分组格式。
## 生成式 UI 规划

项目后续会沿“受控生成式 UI”方向演进：后端 Agent 生成结构化 `uiBlocks`，前端通过白名单组件和 CopilotKit `useRenderTool` 渲染动态 UI。图表状态变更仍然只通过 `ChartAgentAction` 完成。

详细设计见 [docs/generative-ui-design.md](docs/generative-ui-design.md)。
