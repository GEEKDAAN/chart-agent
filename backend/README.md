# 后端

FastAPI 后端 MVP，提供图表 Agent 的协议模型、mock 指标查询和 `/chart-agent/chat` 接口。

## 本地运行

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## 示例请求

```bash
curl -X POST http://localhost:8000/chart-agent/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"conversationId\":\"demo\",\"message\":\"看最近30天各渠道销售额\",\"currentChart\":null,\"pageContext\":{},\"userContext\":{\"userId\":\"u_1\",\"tenantId\":\"t_1\"}}"
```
