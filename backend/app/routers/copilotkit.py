import base64
import json
from collections.abc import Iterable
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from app.schemas.chart import ChartAgentRequest
from app.services.chart_agent import run_chart_agent

router = APIRouter(prefix="/copilotkit", tags=["copilotkit"])

RUNTIME_VERSION = "1.59.5"


@router.get("/threads")
def list_threads(
    response: Response,
    agent_id: str = Query(alias="agentId"),
    include_archived: bool = Query(default=False, alias="includeArchived"),
    limit: int | None = None,
    cursor: str | None = None,
) -> dict[str, Any]:
    response.headers["X-CopilotKit-Runtime-Version"] = RUNTIME_VERSION
    return {
        "threads": [],
        "nextCursor": None,
    }


@router.post("")
def copilotkit_runtime(payload: dict[str, Any], response: Response) -> Any:
    response.headers["X-CopilotKit-Runtime-Version"] = RUNTIME_VERSION

    if payload.get("method") == "info":
        return _runtime_info()

    if payload.get("method") == "agent/run":
        return _generate_agent_run_stream(payload)

    if payload.get("method") == "agent/connect":
        return _generate_agent_connect_stream(payload)

    return {
        "errors": [
            {
                "message": f"Unsupported CopilotKit method: {payload.get('method') or 'unknown'}",
            }
        ]
    }


def _generate_agent_run_stream(payload: dict[str, Any]) -> StreamingResponse:
    body = payload.get("body") or {}
    thread_id = str(body.get("threadId") or f"copilotkit-{uuid4()}")
    run_id = str(body.get("runId") or f"run-{uuid4()}")
    message_id = f"msg-{uuid4()}"

    return StreamingResponse(
        _sse_events(_agui_agent_run_events(thread_id, run_id, message_id, body)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-CopilotKit-Runtime-Version": RUNTIME_VERSION,
        },
    )


def _generate_agent_connect_stream(payload: dict[str, Any]) -> StreamingResponse:
    body = payload.get("body") or {}
    thread_id = str(body.get("threadId") or f"copilotkit-{uuid4()}")
    run_id = str(body.get("runId") or f"connect-{uuid4()}")
    events = [
        {
            "type": "RUN_STARTED",
            "threadId": thread_id,
            "runId": run_id,
            "input": body,
        },
        {
            "type": "RUN_FINISHED",
            "threadId": thread_id,
            "runId": run_id,
        },
    ]

    return StreamingResponse(
        _sse_events(events),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-CopilotKit-Runtime-Version": RUNTIME_VERSION,
        },
    )


def _to_chart_agent_request_from_agui(body: dict[str, Any], thread_id: str) -> ChartAgentRequest:
    message = _last_agui_user_message_content(body.get("messages") or [])
    if not message:
        raise ValueError("CopilotKit agent/run request does not contain a user text message")

    properties = _resolve_agui_runtime_properties(body)
    return ChartAgentRequest.model_validate(
        {
            "conversationId": thread_id,
            "message": message,
            "currentChart": properties.get("currentChart"),
            "pageContext": properties.get("pageContext") or {"source": "copilotkit-agent-run"},
            "userContext": properties.get("userContext")
            or {"userId": "copilotkit_user", "tenantId": "demo"},
        }
    )


def _resolve_agui_runtime_properties(body: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        body.get("forwardedProps"),
        body.get("properties"),
        body.get("chartAgentContext"),
        (body.get("state") or {}).get("chartAgentContext") if isinstance(body.get("state"), dict) else None,
        _extract_context_from_agui_messages(body.get("messages") or []),
    ]
    properties: dict[str, Any] = {}
    for candidate in candidates:
        if isinstance(candidate, dict):
            properties.update(candidate)
    return properties


def _last_agui_user_message_content(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            return _strip_context_marker(content).strip()
        if isinstance(content, list):
            parts = [
                part.get("text")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str)
            ]
            if parts:
                return _strip_context_marker("".join(parts)).strip()
    return ""


def _extract_context_from_agui_messages(messages: list[dict[str, Any]]) -> dict[str, Any]:
    for message in reversed(messages):
        content = message.get("content")
        if isinstance(content, str):
            marker = _extract_json_marker(content, "chart-agent-context")
            if marker:
                return marker
    return {}


def _strip_context_marker(content: str) -> str:
    prefix = "<!-- chart-agent-context:"
    start = content.find(prefix)
    if start < 0:
        return content
    end = content.find(" -->", start)
    if end < 0:
        return content[:start]
    return (content[:start] + content[end + 4 :]).strip()


def _agui_agent_run_events(
    thread_id: str,
    run_id: str,
    message_id: str,
    body: dict[str, Any],
) -> Iterable[dict[str, Any]]:
    yield {
        "type": "RUN_STARTED",
        "threadId": thread_id,
        "runId": run_id,
        "input": body,
    }
    yield {
        "type": "TEXT_MESSAGE_START",
        "messageId": message_id,
        "role": "assistant",
    }

    try:
        yield _text_delta(message_id, "执行状态：正在解析用户需求...\n")
        chart_request = _to_chart_agent_request_from_agui(body, thread_id)

        yield _text_delta(message_id, "执行状态：已读取当前图表上下文，正在规划数据需求...\n")
        yield _text_delta(message_id, "执行状态：正在运行后端 ChartAgent workflow...\n")
        chart_response = run_chart_agent(chart_request)

        yield _text_delta(message_id, "执行状态：已生成图表变更，正在同步到前端...\n\n")
        content = _format_chart_agent_response(chart_response.model_dump(by_alias=True))
        yield _text_delta(message_id, content)
        yield {
            "type": "TEXT_MESSAGE_END",
            "messageId": message_id,
        }
        yield {
            "type": "RUN_FINISHED",
            "threadId": thread_id,
            "runId": run_id,
        }
    except (ValueError, ValidationError) as error:
        message = str(error)
        yield _text_delta(message_id, f"执行状态：处理失败。\n\n失败原因：{message}")
        yield {
            "type": "TEXT_MESSAGE_END",
            "messageId": message_id,
        }
        yield {
            "type": "RUN_ERROR",
            "message": message,
            "code": "chart_agent_error",
        }


def _text_delta(message_id: str, delta: str) -> dict[str, Any]:
    return {
        "type": "TEXT_MESSAGE_CONTENT",
        "messageId": message_id,
        "delta": delta,
    }


def _sse_events(events: Iterable[dict[str, Any]]):
    for event in events:
        yield f"data: {json.dumps(event, ensure_ascii=False, separators=(',', ':'))}\n\n"


def _runtime_info() -> dict[str, Any]:
    return {
        "version": RUNTIME_VERSION,
        "agents": {
            "chart-agent": {
                "name": "chart-agent",
                "className": "chart-agent",
                "description": "生成和编辑受控 ChartSpec 图表。",
                "capabilities": {},
            }
        },
        "audioFileTranscriptionEnabled": False,
        "mode": "sse",
        "a2uiEnabled": False,
        "openGenerativeUIEnabled": False,
        "licenseStatus": "none",
        "telemetryDisabled": True,
    }


def _extract_json_marker(content: str, marker_name: str) -> dict[str, Any] | None:
    prefix = f"<!-- {marker_name}:"
    start = content.find(prefix)
    if start < 0:
        return None
    start += len(prefix)
    end = content.find(" -->", start)
    if end < 0:
        return None
    try:
        decoded = base64.b64decode(content[start:end]).decode("utf-8")
        value = json.loads(decoded)
    except (ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _format_chart_agent_response(response: dict[str, Any]) -> str:
    action = response["action"]
    if action["type"] == "error":
        return action["message"]

    return (
        f"{action['message']}\n\n"
        "当前版本已通过 CopilotKit Runtime 调用后端图表 Agent。"
        "\n\n"
        f"<!-- chart-agent-action:{_encode_action_marker(action)} -->"
    )


def _encode_action_marker(action: dict[str, Any]) -> str:
    raw = json.dumps(action, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")
