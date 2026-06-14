from fastapi.testclient import TestClient

from app.main import app
from app.routers.copilotkit import _progress_steps


client = TestClient(app)


def test_progress_steps_are_specific_to_tool_name():
    create_steps = _progress_steps("create_chart", "running")["steps"]
    update_data_steps = _progress_steps("update_data", "running")["steps"]
    change_type_steps = _progress_steps("change_chart_type", "running")["steps"]

    assert [step["id"] for step in create_steps] == [
        "parse_create_request",
        "plan_data",
        "query_data",
        "generate_chart",
        "sync_frontend",
    ]
    assert [step["id"] for step in update_data_steps] == [
        "parse_data_request",
        "plan_data_update",
        "query_updated_data",
        "generate_data_patch",
        "sync_frontend",
    ]
    assert [step["id"] for step in change_type_steps] == [
        "parse_type_request",
        "read_current_chart",
        "validate_chart_type",
        "generate_type_patch",
        "sync_frontend",
    ]
    assert create_steps[0]["status"] == "running"
    assert all(step["status"] == "pending" for step in create_steps[1:])


def test_progress_steps_mark_all_steps_completed_for_final_snapshot():
    steps = _progress_steps("update_style", "completed")["steps"]

    assert [step["id"] for step in steps] == [
        "parse_style_request",
        "read_current_chart",
        "generate_style_patch",
        "sync_frontend",
    ]
    assert all(step["status"] == "completed" for step in steps)


def test_runtime_info_returns_single_endpoint_metadata():
    response = client.post("/copilotkit", json={"method": "info"})

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "1.59.5"
    assert body["mode"] == "sse"
    assert body["audioFileTranscriptionEnabled"] is False
    assert body["agents"]["chart-agent"]["name"] == "chart-agent"


def test_runtime_info_get_endpoint_returns_metadata_for_copilotkit_client():
    response = client.get("/copilotkit/info")

    assert response.status_code == 200
    assert response.headers["X-CopilotKit-Runtime-Version"] == "1.59.5"
    body = response.json()
    assert body["version"] == "1.59.5"
    assert body["mode"] == "sse"
    assert body["agents"]["chart-agent"]["name"] == "chart-agent"


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


def test_agent_run_single_endpoint_returns_agui_sse_events_with_tool_render_progress():
    response = client.post(
        "/copilotkit",
        json={
            "method": "agent/run",
            "params": {"agentId": "chart-agent"},
            "body": _run_body("thread-agui", "run-agui"),
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    content = response.text
    assert '"type":"RUN_STARTED"' in content
    assert '"type":"TEXT_MESSAGE_CONTENT"' in content
    assert '"type":"TOOL_CALL_START"' in content
    assert '"toolCallName":"chartAgentProgress"' in content
    assert '"type":"TOOL_CALL_ARGS"' in content
    assert '"type":"TOOL_CALL_END"' in content
    assert '"type":"TOOL_CALL_RESULT"' in content
    assert content.count('"type":"TOOL_CALL_RESULT"') > 1
    assert '"id":"parse_create_request"' in content
    assert '"id":"query_data"' in content
    assert '"id":"generate_chart"' in content
    assert '"id":"sync_frontend"' in content
    assert '\\"status\\":\\"running\\"' in content
    assert '\\"status\\":\\"completed\\"' in content
    assert "执行状态：" not in content
    assert "chart-agent-step" not in content
    assert "chart-agent-action" in content
    assert '"type":"RUN_FINISHED"' in content


def test_agent_run_rest_endpoint_returns_agui_sse_events_with_tool_render_progress():
    response = client.post(
        "/copilotkit/agent/chart-agent/run",
        json=_run_body("thread-rest", "run-rest"),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    content = response.text
    assert '"type":"RUN_STARTED"' in content
    assert '"threadId":"thread-rest"' in content
    assert '"type":"TOOL_CALL_START"' in content
    assert '"toolCallName":"chartAgentProgress"' in content
    assert '"id":"parse_create_request"' in content
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
    assert '"type":"TOOL_CALL_START"' in content
    assert '"toolCallName":"chartAgentProgress"' in content
    assert '"id":"parse_style_request"' in content
    assert '"id":"read_current_chart"' in content
    assert '"id":"generate_style_patch"' in content
    assert '"id":"query_data"' not in content
    assert "chart-agent-action" in content


def test_agent_run_streams_failed_progress_when_chart_update_has_no_current_chart():
    response = client.post(
        "/copilotkit",
        json={
            "method": "agent/run",
            "params": {"agentId": "chart-agent"},
            "body": {
                "threadId": "thread-style-no-chart",
                "runId": "run-style-no-chart",
                "messages": [
                    {
                        "id": "user-message-style-no-chart",
                        "role": "user",
                        "content": "把抖音改成红色",
                    }
                ],
                "forwardedProps": {
                    "pageContext": {"source": "test-style-no-chart"},
                    "userContext": {"userId": "u_demo", "tenantId": "t_demo"},
                },
            },
        },
    )

    assert response.status_code == 200
    content = response.text
    assert '"type":"TOOL_CALL_START"' in content
    assert '"toolCallName":"chartAgentProgress"' in content
    assert '"id":"parse_style_request"' in content
    assert '\\"status\\":\\"failed\\"' in content
    assert "chart-agent-action" not in content
    assert '"type":"RUN_FINISHED"' in content


def test_agent_run_uses_current_chart_context_for_chart_questions():
    chart = _create_chart()

    response = client.post(
        "/copilotkit",
        json={
            "method": "agent/run",
            "params": {"agentId": "chart-agent"},
            "body": {
                "threadId": "thread-chart-question",
                "runId": "run-chart-question",
                "messages": [
                    {
                        "id": "user-message-chart-question",
                        "role": "user",
                        "content": "这个图表相关信息是什么？",
                    }
                ],
                "forwardedProps": {
                    "currentChart": chart,
                    "pageContext": {"source": "test-chart-question"},
                    "userContext": {"userId": "u_demo", "tenantId": "t_demo"},
                },
            },
        },
    )

    assert response.status_code == 200
    content = response.text
    assert '"type":"TOOL_CALL_START"' not in content
    assert "chartAgentProgress" not in content
    assert "当前图表" in content
    assert "我还不能确定你的图表需求" not in content
    assert "chart-agent-action" not in content
    assert '"type":"RUN_FINISHED"' in content


def test_agent_run_answers_current_chart_dimension_question_without_progress():
    chart = _create_chart()

    response = client.post(
        "/copilotkit",
        json={
            "method": "agent/run",
            "params": {"agentId": "chart-agent"},
            "body": {
                "threadId": "thread-chart-dimension-question",
                "runId": "run-chart-dimension-question",
                "messages": [
                    {
                        "id": "user-message-chart-dimension-question",
                        "role": "user",
                        "content": "有哪些渠道？",
                    }
                ],
                "forwardedProps": {
                    "currentChart": chart,
                    "pageContext": {"source": "test-chart-dimension-question"},
                    "userContext": {"userId": "u_demo", "tenantId": "t_demo"},
                },
            },
        },
    )

    assert response.status_code == 200
    content = response.text
    assert '"type":"TOOL_CALL_START"' not in content
    assert "chartAgentProgress" not in content
    assert "抖音、小红书、微信、天猫" in content
    assert "chart-agent-action" not in content
    assert '"type":"RUN_FINISHED"' in content


def test_agent_run_rest_endpoint_answers_current_chart_dimension_question_without_progress():
    chart = _create_chart()

    response = client.post(
        "/copilotkit/agent/chart-agent/run",
        json={
            "threadId": "thread-rest-chart-dimension-question",
            "runId": "run-rest-chart-dimension-question",
            "messages": [
                {
                    "id": "user-message-rest-chart-dimension-question",
                    "role": "user",
                    "content": "渠道有哪些？",
                }
            ],
            "forwardedProps": {
                "currentChart": chart,
                "pageContext": {"source": "test-rest-chart-dimension-question"},
                "userContext": {"userId": "u_demo", "tenantId": "t_demo"},
            },
        },
    )

    assert response.status_code == 200
    content = response.text
    assert '"type":"TOOL_CALL_START"' not in content
    assert "chartAgentProgress" not in content
    assert "抖音" in content
    assert "小红书" in content
    assert "微信" in content
    assert "天猫" in content
    assert "chart-agent-action" not in content
    assert '"type":"RUN_FINISHED"' in content


def test_agent_run_answers_current_chart_metric_lookup_without_progress():
    chart = _create_chart()

    response = client.post(
        "/copilotkit",
        json={
            "method": "agent/run",
            "params": {"agentId": "chart-agent"},
            "body": {
                "threadId": "thread-chart-metric-question",
                "runId": "run-chart-metric-question",
                "messages": [
                    {
                        "id": "user-message-chart-metric-question",
                        "role": "user",
                        "content": "抖音的销售额有多少？",
                    }
                ],
                "forwardedProps": {
                    "currentChart": chart,
                    "pageContext": {"source": "test-chart-metric-question"},
                    "userContext": {"userId": "u_demo", "tenantId": "t_demo"},
                },
            },
        },
    )

    assert response.status_code == 200
    content = response.text
    assert '"type":"TOOL_CALL_START"' not in content
    assert "chartAgentProgress" not in content
    assert "168,000" in content
    assert "chart-agent-action" not in content
    assert '"type":"RUN_FINISHED"' in content


def test_agent_run_smalltalk_returns_text_without_progress_tool_or_action_marker():
    response = client.post(
        "/copilotkit",
        json={
            "method": "agent/run",
            "params": {"agentId": "chart-agent"},
            "body": {
                "threadId": "thread-smalltalk",
                "runId": "run-smalltalk",
                "messages": [
                    {
                        "id": "user-message-smalltalk",
                        "role": "user",
                        "content": "你好",
                    }
                ],
                "forwardedProps": {
                    "pageContext": {"source": "test-smalltalk"},
                    "userContext": {"userId": "u_demo", "tenantId": "t_demo"},
                },
            },
        },
    )

    assert response.status_code == 200
    content = response.text
    assert '"type":"RUN_STARTED"' in content
    assert '"type":"TEXT_MESSAGE_CONTENT"' in content
    assert "你好，我是 chart-agent" in content
    assert "chartAgentProgress" not in content
    assert "chart-agent-action" not in content
    assert '"type":"RUN_FINISHED"' in content


def test_agent_connect_rest_endpoint_returns_agui_sse_events():
    response = client.post(
        "/copilotkit/agent/chart-agent/connect",
        json={
            "threadId": "thread-rest-connect",
            "runId": "run-rest-connect",
            "messages": [],
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    content = response.text
    assert '"type":"RUN_STARTED"' in content
    assert '"threadId":"thread-rest-connect"' in content
    assert '"type":"RUN_FINISHED"' in content


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
    assert '"type":"TOOL_CALL_START"' not in content
    assert "chartAgentProgress" not in content
    assert "CopilotKit agent/run request does not contain a user text message" in content
    assert '"type":"RUN_ERROR"' in content


def _run_body(thread_id: str, run_id: str) -> dict:
    return {
        "threadId": thread_id,
        "runId": run_id,
        "messages": [
            {
                "id": f"user-message-{run_id}",
                "role": "user",
                "content": "看最近30天各渠道销售额",
            }
        ],
        "forwardedProps": {
            "pageContext": {"source": "test"},
            "userContext": {"userId": "u_demo", "tenantId": "t_demo"},
        },
    }


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
