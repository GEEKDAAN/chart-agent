# 测试规范

本文档定义 chart-agent 的测试分层、运行命令和验收标准。项目当前没有 CI，所有关键变更必须在本地完成对应验证并向用户说明结果。

## 测试分层

```text
后端单元/API测试
  验证 FastAPI、LangGraph workflow、意图决策、数据需求解析、指标服务。

Runtime 契约测试
  验证 CopilotKit 官方 Runtime、AG-UI 工具事件、后端转发和健康检查。

前端构建测试
  验证 TypeScript、Vite 构建和浏览器端依赖边界。

Playwright E2E
  验证 CopilotKit 侧边栏、上下文传递、图表生成/编辑/问答连续流程。

文本编码检查
  验证源码、测试、文档中没有典型中文乱码。
```

## 常用命令

后端：

```powershell
cd backend
$env:CHART_AGENT_LLM_MODE='off'
python -m pytest -q
```

Runtime：

```powershell
cd runtime
npm.cmd run test
npm.cmd run build
npm.cmd run check:text
```

前端：

```powershell
cd frontend
npm.cmd run build
npm.cmd run test:e2e
```

本地三服务：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1 -LlmMode off
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1 -LlmMode openai
powershell -ExecutionPolicy Bypass -File scripts/stop-dev.ps1
```

## 变更类型与最低测试要求

| 变更类型 | 最低测试 |
| --- | --- |
| 后端 schema/action/Agent | `backend` pytest |
| 意图决策/fallback/LLM guardrail | `backend` pytest，必须覆盖决策矩阵 |
| Runtime 事件/健康检查/上下文转发 | Runtime test + build |
| 前端类型/ChartSpec/ECharts | Frontend build |
| CopilotKit 交互/上下文/工具渲染 | Frontend E2E |
| 文档/中文文案大量变更 | `runtime` check:text |

## 意图决策矩阵

凡是新增或调整以下能力，必须更新 `backend/tests/test_intent_decision_matrix.py`：

- 新建图表
- 当前图表问答
- 样式修改
- 隐藏或恢复显示
- 切换图表类型
- 新增指标或数据更新
- 闲聊、帮助、越界、澄清

矩阵用例必须同时覆盖：

- 无当前图表
- 有当前图表
- 当前图表与新请求维度不同
- LLM 误判但后端 guardrail 回退

## E2E 规则

E2E 不追求覆盖所有细节，优先覆盖真实用户连续路径：

```text
生成图表 -> 修改图表 -> 当前图表问答
生成趋势图 -> 生成渠道图 -> 当前渠道追问
样式修改 -> 继续样式修改 -> 当前图表问答
```

E2E 应尽量断言后端 action 的结构，例如 chart type、encoding、是否触发 `chartAgentProgress` 和 `chartAgentAction`。

## 验收汇报格式

完成实现后必须向用户说明：

- 如何测试的。
- 测试结果。
- 是否存在问题。
- 存在问题时说明原因和建议调整。
- 是否已提交；未提交时说明原因。

## 已知非阻塞问题

- 后端测试可能出现 Starlette/httpx2 deprecation warning，目前不影响功能。
- GitHub push 可能受本地网络影响失败；本地 commit 成功和远程 push 状态需要分别说明。
