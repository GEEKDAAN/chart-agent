import base64
import json
import logging
from collections.abc import Iterable
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from app.agents.chart_agent_graph import build_chart_agent_graph
from app.schemas.chart import ChartAgentAction, ChartAgentRequest, ChartAgentResponse
from app.core.config import get_settings
from app.services.llm_decisions import decide_chart_agent_tool

router = APIRouter(prefix="/copilotkit", tags=["copilotkit"])

RUNTIME_VERSION = "1.59.5"
logger = logging.getLogger("uvicorn.error")
_NON_FAILURE_ACTION_CODES = {"explanation", "smalltalk", "help", "out_of_scope", "clarification_required"}


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
    _log_runtime_context_debug(thread_id, message, properties)
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


def _log_runtime_context_debug(thread_id: str, message: str, properties: dict[str, Any]) -> None:
    if get_settings().app_env == "production":
        return
    logger.info(
        "chart-agent runtime context: threadId=%s messageLength=%s hasCurrentChart=%s",
        thread_id,
        len(message),
        bool(properties.get("currentChart")),
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
        chart_request = _to_chart_agent_request_from_agui(body, thread_id)
        decision = _decide_runtime_tool(chart_request)
        intent = decision.intent
        tool_name = decision.toolName

        should_render_progress = _should_render_progress(tool_name)
        progress_sequence = 0
        if should_render_progress:
            progress = _with_progress_metadata(_progress_steps(tool_name, "running"), tool_call_id, progress_sequence)
            yield _tool_call_start(message_id, tool_call_id, progress)
            yield _tool_call_args(tool_call_id, progress)

        chart_response = None
        last_node_name = ""
        last_workflow_state: dict[str, Any] = {}
        for workflow_event in _stream_chart_agent(chart_request, decision):
            if workflow_event["type"] == "progress" and should_render_progress:
                last_node_name = workflow_event["nodeName"]
                last_workflow_state = workflow_event["state"]
                progress = _progress_steps_for_node(
                    tool_name,
                    last_node_name,
                    last_workflow_state,
                )
                progress_sequence += 1
                yield _tool_call_result(
                    tool_call_id,
                    _with_progress_metadata(progress, tool_call_id, progress_sequence),
                )
            if workflow_event["type"] == "final":
                chart_response = workflow_event["response"]

        if chart_response is None:
            raise ValueError("Chart agent stream did not produce a final response")

        if should_render_progress:
            final_progress = (
                _failed_progress_for_final_action(
                    tool_name,
                    last_node_name,
                    last_workflow_state,
                    chart_response.action.message,
                )
                if chart_response.action.type == "error" and chart_response.action.code not in _NON_FAILURE_ACTION_CODES
                else _progress_steps(tool_name, "completed")
            )
            progress_sequence += 1
            yield _tool_call_result(
                tool_call_id,
                _with_progress_metadata(final_progress, tool_call_id, progress_sequence, is_final=True),
            )
            yield _tool_call_end(tool_call_id)

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


def _should_render_progress(tool_name: str) -> bool:
    return tool_name in {"create_chart", "update_style", "update_data", "change_chart_type"}


def _decide_runtime_tool(chart_request: ChartAgentRequest):
    return decide_chart_agent_tool(
        {
            "conversation_id": chart_request.conversation_id,
            "user_message": chart_request.message,
            "current_chart": chart_request.current_chart,
            "page_context": chart_request.page_context,
            "user_context": chart_request.user_context,
            "data_requirements": None,
            "queried_data": None,
            "chart_action": None,
            "assistant_message": "",
            "errors": [],
        }
    )


def _stream_chart_agent(chart_request: ChartAgentRequest, decision) -> Iterable[dict[str, Any]]:
    initial_state = {
        "conversation_id": chart_request.conversation_id,
        "user_message": chart_request.message,
        "current_chart": chart_request.current_chart,
        "page_context": chart_request.page_context,
        "user_context": chart_request.user_context,
        "decision": decision,
        "data_requirements": None,
        "queried_data": None,
        "chart_action": None,
        "assistant_message": "",
        "errors": [],
    }
    final_state = initial_state
    for update in build_chart_agent_graph().stream(initial_state):
        for node_name, node_state in update.items():
            final_state = node_state
            yield {"type": "progress", "nodeName": node_name, "state": node_state}

    action = final_state.get("chart_action") or ChartAgentAction(
        type="error",
        code="agent_no_action",
        message="Agent 未生成有效图表动作。",
    )
    yield {
        "type": "final",
        "response": ChartAgentResponse(
            conversationId=chart_request.conversation_id,
            intent=final_state.get("intent", "unknown"),
            action=action,
        ),
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


def _legacy_progress_steps(state: str, error_message: str | None = None) -> dict[str, Any]:
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


def _progress_steps(tool_name: str, state: str, error_message: str | None = None) -> dict[str, Any]:
    templates = {
        "create_chart": [
            ("parse_create_request", "识别图表需求", "正在识别指标、维度和时间范围", "已识别图表生成需求"),
            ("plan_data", "规划数据查询", "等待生成数据需求", "已完成指标、维度和筛选条件规划"),
            ("query_data", "查询业务数据", "等待查询数据", "已获得图表所需数据"),
            ("generate_chart", "生成图表配置", "等待生成受控 ChartSpec", "已生成图表配置"),
            ("sync_frontend", "同步到前端", "等待应用图表", "图表已同步到前端"),
        ],
        "update_style": [
            ("parse_style_request", "识别样式修改", "正在识别颜色、系列或展示样式目标", "已识别样式修改目标"),
            ("read_current_chart", "读取当前图表", "等待读取当前 ChartSpec", "已读取当前图表上下文"),
            ("generate_style_patch", "生成样式变更", "等待生成受控样式 patch", "已生成样式变更"),
            ("sync_frontend", "同步到前端", "等待应用样式", "样式修改已同步到前端"),
        ],
        "update_data": [
            ("parse_data_request", "识别数据修改", "正在识别新增指标或数据调整目标", "已识别数据修改需求"),
            ("plan_data_update", "规划数据补充", "等待规划补充数据", "已完成补充数据规划"),
            ("query_updated_data", "查询更新数据", "等待查询更新后的数据", "已获得更新后的图表数据"),
            ("generate_data_patch", "生成数据变更", "等待生成受控数据 patch", "已生成数据变更"),
            ("sync_frontend", "同步到前端", "等待应用数据变更", "数据修改已同步到前端"),
        ],
        "change_chart_type": [
            ("parse_type_request", "识别图表类型", "正在识别目标图表类型", "已识别目标图表类型"),
            ("read_current_chart", "读取当前图表", "等待读取当前 ChartSpec", "已读取当前图表上下文"),
            ("validate_chart_type", "校验数据适配", "等待校验当前数据是否适合目标类型", "已完成图表类型适配校验"),
            ("generate_type_patch", "生成类型变更", "等待生成受控类型 patch", "已生成图表类型变更"),
            ("sync_frontend", "同步到前端", "等待应用类型变更", "图表类型已同步到前端"),
        ],
    }
    template = templates.get(tool_name, templates["create_chart"])

    steps = []
    for index, (step_id, title, running_detail, completed_detail) in enumerate(template):
        if state == "completed":
            status = "completed"
            detail = completed_detail
        elif state == "failed" and index == 0:
            status = "failed"
            detail = f"处理失败：{error_message}" if error_message else "处理失败"
        elif state == "running" and index == 0:
            status = "running"
            detail = running_detail
        else:
            status = "pending"
            detail = running_detail
        steps.append({"id": step_id, "title": title, "detail": detail, "status": status})
    return {"steps": steps}


def _progress_steps_for_node(tool_name: str, node_name: str, workflow_state: dict[str, Any]) -> dict[str, Any]:
    failed_step = _failed_step_for_state(tool_name, node_name, workflow_state)
    if failed_step:
        return _progress_steps_with_marks(
            tool_name,
            completed=_completed_steps_before(tool_name, failed_step),
            running=None,
            failed=failed_step,
            error_message=(workflow_state.get("errors") or ["处理失败"])[0],
        )

    completed = _completed_steps_for_node(tool_name, node_name)
    running = _running_step_after_node(tool_name, node_name)
    return _progress_steps_with_marks(tool_name, completed=completed, running=running)


def _progress_steps_with_marks(
    tool_name: str,
    completed: set[str],
    running: str | None = None,
    failed: str | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    snapshot = _progress_steps(tool_name, "running")
    for step in snapshot["steps"]:
        step_id = step["id"]
        if step_id in completed:
            step["status"] = "completed"
            step["detail"] = _completed_detail(tool_name, step_id)
        elif step_id == failed:
            step["status"] = "failed"
            step["detail"] = f"处理失败：{error_message}" if error_message else "处理失败"
        elif step_id == running:
            step["status"] = "running"
        else:
            step["status"] = "pending"
    return snapshot


def _with_progress_metadata(
    progress: dict[str, Any],
    progress_id: str,
    sequence: int,
    is_final: bool = False,
) -> dict[str, Any]:
    return {**progress, "progressId": progress_id, "sequence": sequence, "isFinal": is_final}


def _completed_steps_for_node(tool_name: str, node_name: str) -> set[str]:
    mapping = {
        "create_chart": {
            "decide_tool": {"parse_create_request"},
            "plan_data": {"parse_create_request", "plan_data"},
            "query_data": {"parse_create_request", "plan_data", "query_data"},
            "generate_action": {"parse_create_request", "plan_data", "query_data", "generate_chart"},
            "validate_action": {"parse_create_request", "plan_data", "query_data", "generate_chart"},
            "respond": {"parse_create_request", "plan_data", "query_data", "generate_chart", "sync_frontend"},
        },
        "update_style": {
            "decide_tool": {"parse_style_request"},
            "generate_action": {"parse_style_request", "read_current_chart", "generate_style_patch"},
            "validate_action": {"parse_style_request", "read_current_chart", "generate_style_patch"},
            "respond": {"parse_style_request", "read_current_chart", "generate_style_patch", "sync_frontend"},
        },
        "update_data": {
            "decide_tool": {"parse_data_request"},
            "plan_data": {"parse_data_request", "plan_data_update"},
            "query_data": {"parse_data_request", "plan_data_update", "query_updated_data"},
            "generate_action": {
                "parse_data_request",
                "plan_data_update",
                "query_updated_data",
                "generate_data_patch",
            },
            "validate_action": {
                "parse_data_request",
                "plan_data_update",
                "query_updated_data",
                "generate_data_patch",
            },
            "respond": {
                "parse_data_request",
                "plan_data_update",
                "query_updated_data",
                "generate_data_patch",
                "sync_frontend",
            },
        },
        "change_chart_type": {
            "decide_tool": {"parse_type_request"},
            "generate_action": {"parse_type_request", "read_current_chart", "validate_chart_type", "generate_type_patch"},
            "validate_action": {"parse_type_request", "read_current_chart", "validate_chart_type", "generate_type_patch"},
            "respond": {
                "parse_type_request",
                "read_current_chart",
                "validate_chart_type",
                "generate_type_patch",
                "sync_frontend",
            },
        },
    }
    return set(mapping.get(tool_name, {}).get(node_name, set()))


def _running_step_after_node(tool_name: str, node_name: str) -> str | None:
    mapping = {
        "create_chart": {
            "decide_tool": "plan_data",
            "plan_data": "query_data",
            "query_data": "generate_chart",
            "generate_action": "sync_frontend",
            "validate_action": "sync_frontend",
        },
        "update_style": {
            "decide_tool": "read_current_chart",
            "generate_action": "sync_frontend",
            "validate_action": "sync_frontend",
        },
        "update_data": {
            "decide_tool": "plan_data_update",
            "plan_data": "query_updated_data",
            "query_data": "generate_data_patch",
            "generate_action": "sync_frontend",
            "validate_action": "sync_frontend",
        },
        "change_chart_type": {
            "decide_tool": "read_current_chart",
            "generate_action": "sync_frontend",
            "validate_action": "sync_frontend",
        },
    }
    return mapping.get(tool_name, {}).get(node_name)


def _failed_step_for_state(tool_name: str, node_name: str, workflow_state: dict[str, Any]) -> str | None:
    if not workflow_state.get("errors"):
        return None
    fallback = _running_step_after_node(tool_name, node_name)
    if fallback:
        return fallback
    completed = _completed_steps_for_node(tool_name, node_name)
    return next((step["id"] for step in _progress_steps(tool_name, "running")["steps"] if step["id"] not in completed), None)


def _failed_progress_for_final_action(
    tool_name: str,
    node_name: str,
    workflow_state: dict[str, Any],
    error_message: str,
) -> dict[str, Any]:
    failed_step = _failed_step_for_state(tool_name, node_name, workflow_state)
    if not failed_step:
        failed_step = {
            "create_chart": "generate_chart",
            "update_style": "read_current_chart",
            "update_data": "generate_data_patch",
            "change_chart_type": "read_current_chart",
        }.get(tool_name, _progress_steps(tool_name, "running")["steps"][0]["id"])
    return _progress_steps_with_marks(
        tool_name,
        completed=_completed_steps_before(tool_name, failed_step),
        failed=failed_step,
        error_message=error_message,
    )


def _completed_steps_before(tool_name: str, step_id: str) -> set[str]:
    completed = set()
    for step in _progress_steps(tool_name, "running")["steps"]:
        if step["id"] == step_id:
            return completed
        completed.add(step["id"])
    return completed


def _completed_detail(tool_name: str, step_id: str) -> str:
    for step in _progress_steps(tool_name, "completed")["steps"]:
        if step["id"] == step_id:
            return step["detail"]
    return "已完成"


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
