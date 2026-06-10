import base64
import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Response
from pydantic import ValidationError

from app.schemas.chart import ChartAgentRequest
from app.services.chart_agent import run_chart_agent

router = APIRouter(prefix="/copilotkit", tags=["copilotkit"])

RUNTIME_VERSION = "1.59.5"


@router.post("")
def copilotkit_runtime(payload: dict[str, Any], response: Response) -> dict[str, Any]:
    response.headers["X-CopilotKit-Runtime-Version"] = RUNTIME_VERSION

    operation_name = payload.get("operationName") or _infer_operation_name(payload.get("query", ""))
    variables = payload.get("variables") or {}

    if operation_name == "availableAgents":
        return {"data": {"availableAgents": _available_agents()}}

    if operation_name == "loadAgentState":
        return {"data": {"loadAgentState": _load_agent_state(variables)}}

    if operation_name == "generateCopilotResponse":
        return {"data": {"generateCopilotResponse": _generate_copilot_response(variables)}}

    return {
        "errors": [
            {
                "message": f"Unsupported CopilotKit operation: {operation_name or 'unknown'}",
            }
        ]
    }


def _infer_operation_name(query: str) -> str | None:
    if "generateCopilotResponse" in query:
        return "generateCopilotResponse"
    if "availableAgents" in query:
        return "availableAgents"
    if "loadAgentState" in query:
        return "loadAgentState"
    return None


def _available_agents() -> dict[str, Any]:
    return {
        "__typename": "AgentsResponse",
        "agents": [
            {
                "__typename": "Agent",
                "name": "chart-agent",
                "id": "chart-agent",
                "description": "生成和编辑受控 ChartSpec 图表。",
            }
        ],
    }


def _load_agent_state(variables: dict[str, Any]) -> dict[str, Any]:
    data = variables.get("data") or {}
    thread_id = data.get("threadId") or f"copilotkit-{uuid4()}"
    return {
        "__typename": "LoadAgentStateResponse",
        "threadId": thread_id,
        "threadExists": False,
        "state": "{}",
        "messages": "[]",
    }


def _generate_copilot_response(variables: dict[str, Any]) -> dict[str, Any]:
    data = variables.get("data") or {}
    properties = _resolve_runtime_properties(variables)
    thread_id = data.get("threadId") or f"copilotkit-{uuid4()}"
    run_id = data.get("runId") or f"run-{uuid4()}"
    parent_message_id = _last_user_message_id(data.get("messages") or [])

    try:
        chart_request = _to_chart_agent_request(data, properties, thread_id)
        chart_response = run_chart_agent(chart_request)
        content = _format_chart_agent_response(chart_response.model_dump(by_alias=True))
        status = _success_response_status()
    except (ValueError, ValidationError) as error:
        content = f"请求无法处理：{error}"
        status = _failed_response_status(str(error))

    return {
        "__typename": "CopilotResponse",
        "threadId": thread_id,
        "runId": run_id,
        "extensions": {
            "__typename": "ExtensionsResponse",
            "openaiAssistantAPI": None,
        },
        "status": status,
        "messages": [
            {
                "__typename": "TextMessageOutput",
                "id": f"msg-{uuid4()}",
                "createdAt": _now_iso(),
                "content": [content],
                "role": "assistant",
                "parentMessageId": parent_message_id,
                "status": _success_message_status(),
            }
        ],
        "metaEvents": [],
    }


def _to_chart_agent_request(
    data: dict[str, Any],
    properties: dict[str, Any],
    thread_id: str,
) -> ChartAgentRequest:
    message = _last_user_message_content(data.get("messages") or [])
    if not message:
        raise ValueError("CopilotKit request does not contain a user text message")

    return ChartAgentRequest.model_validate(
        {
            "conversationId": thread_id,
            "message": message,
            "currentChart": properties.get("currentChart"),
            "pageContext": properties.get("pageContext") or {"source": "copilotkit"},
            "userContext": properties.get("userContext")
            or {"userId": "copilotkit_user", "tenantId": "demo"},
        }
    )


def _resolve_runtime_properties(variables: dict[str, Any]) -> dict[str, Any]:
    data = variables.get("data") or {}
    metadata = data.get("metadata") or {}
    candidates = [
        variables.get("properties"),
        data.get("properties"),
        metadata.get("chartAgentContext"),
        metadata.get("properties"),
        (data.get("frontend") or {}).get("chartAgentContext"),
        _extract_context_from_messages(data.get("messages") or []),
    ]

    properties: dict[str, Any] = {}
    for candidate in candidates:
        if isinstance(candidate, dict):
            properties.update(candidate)
    return properties


def _last_user_message_content(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        text_message = message.get("textMessage")
        if text_message and text_message.get("role") == "user":
            return str(text_message.get("content") or "").strip()
    return ""


def _extract_context_from_messages(messages: list[dict[str, Any]]) -> dict[str, Any]:
    for message in reversed(messages):
        text_message = message.get("textMessage")
        content = text_message.get("content") if text_message else None
        if not isinstance(content, str):
            continue
        marker = _extract_json_marker(content, "chart-agent-context")
        if marker:
            return marker
    return {}


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


def _last_user_message_id(messages: list[dict[str, Any]]) -> str | None:
    for message in reversed(messages):
        text_message = message.get("textMessage")
        if text_message and text_message.get("role") == "user":
            return message.get("id")
    return None


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


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _success_response_status() -> dict[str, str]:
    return {"__typename": "SuccessResponseStatus", "code": "Success"}


def _failed_response_status(reason: str) -> dict[str, Any]:
    return {
        "__typename": "FailedResponseStatus",
        "code": "Failed",
        "reason": "UNKNOWN_ERROR",
        "details": {"message": reason},
    }


def _success_message_status() -> dict[str, str]:
    return {"__typename": "SuccessMessageStatus", "code": "Success"}
