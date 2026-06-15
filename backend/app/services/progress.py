from typing import Any


PROGRESS_TOOL_NAMES = {"create_chart", "update_style", "update_data", "change_chart_type"}

_STEP_TEMPLATES = {
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

_COMPLETED_BY_NODE = {
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
        "generate_action": {"parse_data_request", "plan_data_update", "query_updated_data", "generate_data_patch"},
        "validate_action": {"parse_data_request", "plan_data_update", "query_updated_data", "generate_data_patch"},
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
        "respond": {"parse_type_request", "read_current_chart", "validate_chart_type", "generate_type_patch", "sync_frontend"},
    },
}

_RUNNING_AFTER_NODE = {
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


def should_render_progress(tool_name: str) -> bool:
    return tool_name in PROGRESS_TOOL_NAMES


def progress_steps(tool_name: str, state: str, error_message: str | None = None) -> dict[str, Any]:
    template = _STEP_TEMPLATES.get(tool_name, _STEP_TEMPLATES["create_chart"])
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


def progress_steps_for_node(tool_name: str, node_name: str, workflow_state: dict[str, Any]) -> dict[str, Any]:
    failed_step = _failed_step_for_state(tool_name, node_name, workflow_state)
    if failed_step:
        return _progress_steps_with_marks(
            tool_name,
            completed=_completed_steps_before(tool_name, failed_step),
            failed=failed_step,
            error_message=(workflow_state.get("errors") or ["处理失败"])[0],
        )

    completed = _completed_steps_for_node(tool_name, node_name)
    running = _running_step_after_node(tool_name, node_name)
    return _progress_steps_with_marks(tool_name, completed=completed, running=running)


def failed_progress_for_final_action(
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
        }.get(tool_name, progress_steps(tool_name, "running")["steps"][0]["id"])
    return _progress_steps_with_marks(
        tool_name,
        completed=_completed_steps_before(tool_name, failed_step),
        failed=failed_step,
        error_message=error_message,
    )


def with_progress_metadata(
    progress: dict[str, Any],
    progress_id: str,
    sequence: int,
    is_final: bool = False,
) -> dict[str, Any]:
    return {**progress, "progressId": progress_id, "sequence": sequence, "isFinal": is_final}


def _progress_steps_with_marks(
    tool_name: str,
    completed: set[str],
    running: str | None = None,
    failed: str | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    snapshot = progress_steps(tool_name, "running")
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


def _completed_steps_for_node(tool_name: str, node_name: str) -> set[str]:
    return set(_COMPLETED_BY_NODE.get(tool_name, {}).get(node_name, set()))


def _running_step_after_node(tool_name: str, node_name: str) -> str | None:
    return _RUNNING_AFTER_NODE.get(tool_name, {}).get(node_name)


def _failed_step_for_state(tool_name: str, node_name: str, workflow_state: dict[str, Any]) -> str | None:
    if not workflow_state.get("errors"):
        return None
    fallback = _running_step_after_node(tool_name, node_name)
    if fallback:
        return fallback
    completed = _completed_steps_for_node(tool_name, node_name)
    return next((step["id"] for step in progress_steps(tool_name, "running")["steps"] if step["id"] not in completed), None)


def _completed_steps_before(tool_name: str, step_id: str) -> set[str]:
    completed = set()
    for step in progress_steps(tool_name, "running")["steps"]:
        if step["id"] == step_id:
            return completed
        completed.add(step["id"])
    return completed


def _completed_detail(tool_name: str, step_id: str) -> str:
    for step in progress_steps(tool_name, "completed")["steps"]:
        if step["id"] == step_id:
            return step["detail"]
    return "已完成"
