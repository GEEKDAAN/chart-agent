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
