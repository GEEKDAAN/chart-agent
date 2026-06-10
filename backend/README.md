# 后端

FastAPI 后端 MVP，提供图表 Agent 的协议模型、LangGraph workflow、mock 指标查询和 `/chart-agent/chat` 接口。

## Agent workflow

当前后端使用一个 `ChartAgent` graph，节点包括：

```text
classify_intent
  -> plan_data
  -> query_data
  -> generate_action
  -> validate_action
  -> respond
```

其中样式修改、图表类型切换和图表解释不会进入数据查询节点；创建图表和新增指标会通过 mock 指标服务查询数据。

## 指标服务层

后端通过 `app.services.metrics` 暴露受控指标能力，Agent 只依赖三个稳定函数：

- `get_metric_catalog(user_context)`：返回当前可用指标和维度。
- `validate_data_access(user_context, metrics, dimensions)`：校验用户上下文、指标和维度是否允许访问。
- `query_metrics(metrics, dimensions, filters, time_range, limit)`：返回标准 `ChartData`。

内部实现已经拆为 `MetricService`、`MetricCatalog` 和 `MetricDataSource`。当前默认数据源是 `MockMetricDataSource`，后续接数据库、BI API 或语义指标平台时，优先新增一个实现 `MetricDataSource` 协议的数据源，不直接改 Agent workflow。

## LLM 配置

默认关闭真实 LLM，后端使用确定性 fallback 生成 action。

```bash
CHART_AGENT_LLM_MODE=off
```

如需启用 OpenAI 结构化输出：

```bash
CHART_AGENT_LLM_MODE=openai
OPENAI_API_KEY=你的密钥
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=
```

启用后，`generate_action` 节点会先尝试调用 LLM 生成 `ChartAgentAction`。如果未配置密钥、调用失败或输出校验失败，会自动回退到确定性生成逻辑。

后端优先使用 Responses API 的 JSON schema 输出；如果兼容服务不支持 Responses API，会回退到 Chat Completions 的 JSON object 输出。

如果使用 OpenAI-compatible 服务，可以设置自定义请求地址：

```bash
CHART_AGENT_LLM_MODE=openai
OPENAI_API_KEY=你的密钥
OPENAI_MODEL=gpt-5.5
OPENAI_BASE_URL=https://ai.allrealai.com/v1
```

本地也可以复制 `backend/.env.example` 为 `backend/.env` 后填写配置；`.env` 文件不会提交到 Git。

## CopilotKit Runtime

后端提供 `/copilotkit` 作为 CopilotKit Runtime 最小兼容端点，当前支持：

- `availableAgents`
- `loadAgentState`
- `generateCopilotResponse`

`generateCopilotResponse` 会读取 CopilotKit 消息中的最后一条用户文本，并结合前端通过 `properties.currentChart` 传入的当前图表上下文，转接到现有 `ChartAgent` workflow。

当前版本会在 assistant 文本响应中附带不可见的 `ChartAgentAction` 标记，前端会解析该标记并自动应用图表变更。CopilotKit 流式响应会在后续版本接入。

## 本地运行

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## 测试

```bash
cd backend
python -m pytest
```

## 示例请求

```bash
curl -X POST http://localhost:8000/chart-agent/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"conversationId\":\"demo\",\"message\":\"看最近30天各渠道销售额\",\"currentChart\":null,\"pageContext\":{},\"userContext\":{\"userId\":\"u_1\",\"tenantId\":\"t_1\"}}"
```
