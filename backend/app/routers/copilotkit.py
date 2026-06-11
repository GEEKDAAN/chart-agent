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


@router.get("/info")
def get_runtime_info(response: Response) -> dict[str, Any]:
    response.headers["X-CopilotKit-Runtime-Version"] = RUNTIME_VERSION
    return _runtime_info()


@router.post("/agent/{agent_id}/run")
def run_agent(agent_id: str, body: dict[str, Any]) -> StreamingResponse:
    return _generate_agent_run_stream(
        {
            "params": {"agentId": agent_id},
            "body": body,
        }
    )


@router.post("/agent/{agent_id}/connect")
def connect_agent(agent_id: str, body: dict[str, Any]) -> StreamingResponse:
    return _generate_agent_connect_stream(
        {
            "params": {"agentId": agent_id},
            "body": body,
        }
    )


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
        _sse_events(_structured_agui_agent_run_events(thread_id, run_id, message_id, body)),
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


def _structured_agui_agent_run_events(
    thread_id: str,
    run_id: str,
    message_id: str,
    body: dict[str, Any],
) -> Iterable[dict[str, Any]]:
    tool_call_id = f"tool-{uuid4()}"
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
        yield _tool_call_start(message_id, tool_call_id, _progress_steps("running"))
        yield _tool_call_args(tool_call_id, _progress_steps("running"))
        chart_request = _to_chart_agent_request_from_agui(body, thread_id)
        chart_response = run_chart_agent(chart_request)

        yield _tool_call_end(tool_call_id)
        yield _tool_call_result(tool_call_id, _progress_steps("completed"))
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
        yield _tool_call_end(tool_call_id)
        yield _tool_call_result(tool_call_id, _progress_steps("failed", message))
        yield _text_delta(message_id, f"处理失败：{message}")
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


def _tool_call_start(message_id: str, tool_call_id: str, parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "TOOL_CALL_START",
        "toolCallId": tool_call_id,
        "toolCallName": "chartAgentProgress",
        "parentMessageId": message_id,
        "timestamp": _event_timestamp(),
        "rawEvent": {"parameters": parameters},
    }


def _tool_call_args(tool_call_id: str, parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "TOOL_CALL_ARGS",
        "toolCallId": tool_call_id,
        "delta": json.dumps(parameters, ensure_ascii=False, separators=(",", ":")),
        "timestamp": _event_timestamp(),
    }


def _tool_call_end(tool_call_id: str) -> dict[str, Any]:
    return {
        "type": "TOOL_CALL_END",
        "toolCallId": tool_call_id,
        "timestamp": _event_timestamp(),
    }


def _tool_call_result(tool_call_id: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "TOOL_CALL_RESULT",
        "messageId": f"tool-result-{tool_call_id}",
        "toolCallId": tool_call_id,
        "content": json.dumps(result, ensure_ascii=False, separators=(",", ":")),
        "role": "tool",
        "timestamp": _event_timestamp(),
    }


def _progress_steps(state: str, error_message: str | None = None) -> dict[str, Any]:
    if state == "failed":
        parse_status = "failed"
        parse_detail = f"处理失败：{error_message}" if error_message else "处理失败"
        other_status = "pending"
    elif state == "completed":
        parse_status = "completed"
        parse_detail = "已完成需求解析"
        other_status = "completed"
    else:
        parse_status = "running"
        parse_detail = "正在识别图表意图、指标和维度"
        other_status = "pending"

    steps = [
        {
            "id": "parse_request",
            "title": "解析用户需求",
            "detail": parse_detail,
            "status": parse_status,
        },
        {
            "id": "read_context",
            "title": "读取图表上下文",
            "detail": "已读取当前图表上下文" if state == "completed" else "等待需求解析完成",
            "status": other_status,
        },
        {
            "id": "plan_data",
            "title": "规划数据需求",
            "detail": "已完成指标、维度和筛选条件规划" if state == "completed" else "等待规划数据需求",
            "status": other_status,
        },
        {
            "id": "run_workflow",
            "title": "运行 Agent Workflow",
            "detail": "后端 ChartAgent workflow 已完成" if state == "completed" else "等待运行后端 workflow",
            "status": other_status,
        },
        {
            "id": "generate_action",
            "title": "生成图表变更",
            "detail": "已生成图表变更指令" if state == "completed" else "等待生成图表变更",
            "status": other_status,
        },
        {
            "id": "sync_frontend",
            "title": "同步到前端",
            "detail": "图表变更已同步到前端" if state == "completed" else "等待同步到前端",
            "status": other_status,
        },
    ]
    return {"steps": steps}


def _event_timestamp() -> int:
    return 0


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
    return _encode_marker(action)


def _encode_marker(value: dict[str, Any]) -> str:
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")
