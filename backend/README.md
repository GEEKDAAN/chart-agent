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
