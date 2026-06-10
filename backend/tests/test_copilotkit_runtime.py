import base64
import json

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_available_agents_returns_chart_agent():
    response = client.post(
        "/copilotkit",
        json={
            "operationName": "availableAgents",
            "query": "query availableAgents { availableAgents { agents { name id description } } }",
            "variables": {},
        },
    )

    assert response.status_code == 200
    assert response.headers["X-CopilotKit-Runtime-Version"] == "1.59.5"
    body = response.json()
    assert body["data"]["availableAgents"]["agents"][0]["id"] == "chart-agent"


def test_generate_copilot_response_calls_chart_agent():
    response = client.post(
        "/copilotkit",
        json={
            "operationName": "generateCopilotResponse",
            "query": "mutation generateCopilotResponse { generateCopilotResponse { threadId } }",
            "variables": {
                "data": {
                    "threadId": "thread-1",
                    "frontend": {"actions": []},
                    "messages": [
                        {
                            "id": "user-message-1",
                            "createdAt": "2026-06-10T00:00:00Z",
                            "textMessage": {
                                "role": "user",
                                "content": "看最近30天各渠道销售额",
                            },
                        }
                    ],
                    "metadata": {"requestType": "Chat"},
                },
                "properties": {
                    "pageContext": {"source": "test"},
                    "userContext": {"userId": "u_demo", "tenantId": "t_demo"},
                },
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    result = body["data"]["generateCopilotResponse"]
    assert result["threadId"] == "thread-1"
    assert result["status"]["code"] == "Success"
    assert result["messages"][0]["role"] == "assistant"
    assert "图表" in result["messages"][0]["content"][0]
    assert _extract_action_marker(result["messages"][0]["content"][0])["type"] == "create_chart"


def test_generate_copilot_response_uses_current_chart_context():
    chart = _create_chart()

    response = client.post(
        "/copilotkit",
        json={
            "operationName": "generateCopilotResponse",
            "query": "mutation generateCopilotResponse { generateCopilotResponse { threadId } }",
            "variables": {
                "data": {
                    "threadId": "thread-2",
                    "frontend": {"actions": []},
                    "messages": [
                        {
                            "id": "user-message-2",
                            "createdAt": "2026-06-10T00:00:00Z",
                            "textMessage": {
                                "role": "user",
                                "content": "把抖音改成红色",
                            },
                        }
                    ],
                    "metadata": {"requestType": "Chat"},
                },
                "properties": {
                    "currentChart": chart,
                    "pageContext": {"source": "test"},
                    "userContext": {"userId": "u_demo", "tenantId": "t_demo"},
                },
            },
        },
    )

    assert response.status_code == 200
    content = response.json()["data"]["generateCopilotResponse"]["messages"][0]["content"][0]
    assert "已将 抖音 调整为指定颜色" in content
    marker = _extract_action_marker(content)
    assert marker["type"] == "update_chart"
    assert marker["patch"]["style"]["colors"] == {"抖音": "#ef4444"}


def test_load_agent_state_returns_empty_state():
    response = client.post(
        "/copilotkit",
        json={
            "operationName": "loadAgentState",
            "query": "query loadAgentState { loadAgentState { threadId } }",
            "variables": {"data": {"threadId": "thread-1", "agentName": "chart-agent"}},
        },
    )

    assert response.status_code == 200
    body = response.json()
    state = body["data"]["loadAgentState"]
    assert state["threadId"] == "thread-1"
    assert state["threadExists"] is False
    assert state["state"] == "{}"


def _create_chart() -> dict:
    response = client.post(
        "/chart-agent/chat",
        json={
            "conversationId": "demo",
            "message": "看最近30天各渠道销售额",
            "currentChart": None,
            "pageContext": {},
            "userContext": {"userId": "u_demo", "tenantId": "t_demo"},
        },
    )
    return response.json()["action"]["chart"]


def _extract_action_marker(content: str) -> dict:
    prefix = "<!-- chart-agent-action:"
    start = content.index(prefix) + len(prefix)
    end = content.index(" -->", start)
    return json.loads(base64.b64decode(content[start:end]).decode("utf-8"))
