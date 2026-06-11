from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_runtime_info_returns_single_endpoint_metadata():
    response = client.post("/copilotkit", json={"method": "info"})

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "1.59.5"
    assert body["mode"] == "sse"
    assert body["audioFileTranscriptionEnabled"] is False
    assert body["agents"]["chart-agent"]["description"] == "生成和编辑受控 ChartSpec 图表。"


def test_threads_endpoint_returns_empty_thread_list():
    response = client.get("/copilotkit/threads?agentId=chart-agent")

    assert response.status_code == 200
    assert response.headers["X-CopilotKit-Runtime-Version"] == "1.59.5"
    assert response.json() == {"threads": [], "nextCursor": None}


def test_copilotkit_preflight_allows_local_vite_ports():
    response = client.options(
        "/copilotkit",
        headers={
            "Origin": "http://127.0.0.1:5177",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5177"


def test_agent_connect_single_endpoint_returns_agui_sse_events():
    response = client.post(
        "/copilotkit",
        json={
            "method": "agent/connect",
            "params": {"agentId": "chart-agent"},
            "body": {
                "threadId": "thread-connect",
                "runId": "run-connect",
                "messages": [],
            },
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    content = response.text
    assert '"type":"RUN_STARTED"' in content
    assert '"threadId":"thread-connect"' in content
    assert '"runId":"run-connect"' in content
    assert '"type":"RUN_FINISHED"' in content


def test_agent_run_single_endpoint_returns_agui_sse_events():
    response = client.post(
        "/copilotkit",
        json={
            "method": "agent/run",
            "params": {"agentId": "chart-agent"},
            "body": {
                "threadId": "thread-agui",
                "runId": "run-agui",
                "messages": [
                    {
                        "id": "user-message-agui",
                        "role": "user",
                        "content": "看最近30天各渠道销售额",
                    }
                ],
                "forwardedProps": {
                    "pageContext": {"source": "test-agui"},
                    "userContext": {"userId": "u_demo", "tenantId": "t_demo"},
                },
            },
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    content = response.text
    assert '"type":"RUN_STARTED"' in content
    assert '"type":"TEXT_MESSAGE_CONTENT"' in content
    assert "执行状态：正在解析用户需求" in content
    assert "执行状态：正在运行后端 ChartAgent workflow" in content
    assert "执行状态：已生成图表变更" in content
    assert "chart-agent-action" in content
    assert '"type":"RUN_FINISHED"' in content


def test_agent_run_uses_forwarded_current_chart_context():
    chart = _create_chart()

    response = client.post(
        "/copilotkit",
        json={
            "method": "agent/run",
            "params": {"agentId": "chart-agent"},
            "body": {
                "threadId": "thread-context",
                "runId": "run-context",
                "messages": [
                    {
                        "id": "user-message-context",
                        "role": "user",
                        "content": "把抖音改成红色",
                    }
                ],
                "forwardedProps": {
                    "currentChart": chart,
                    "pageContext": {"source": "test-context"},
                    "userContext": {"userId": "u_demo", "tenantId": "t_demo"},
                },
            },
        },
    )

    assert response.status_code == 200
    content = response.text
    assert '"type":"TEXT_MESSAGE_CONTENT"' in content
    assert "chart-agent-action" in content


def test_unknown_copilotkit_method_is_not_supported():
    response = client.post(
        "/copilotkit",
        json={"method": "agent/unknown"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "errors": [{"message": "Unsupported CopilotKit method: agent/unknown"}],
    }


def test_agent_run_streams_failure_status_when_user_message_is_missing():
    response = client.post(
        "/copilotkit",
        json={
            "method": "agent/run",
            "params": {"agentId": "chart-agent"},
            "body": {
                "threadId": "thread-error",
                "runId": "run-error",
                "messages": [],
            },
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    content = response.text
    assert '"type":"RUN_STARTED"' in content
    assert "执行状态：正在解析用户需求" in content
    assert "执行状态：处理失败" in content
    assert "CopilotKit agent/run request does not contain a user text message" in content
    assert '"type":"RUN_ERROR"' in content


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
