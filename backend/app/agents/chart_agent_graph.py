from collections.abc import Callable
from typing import Any, Literal

from langgraph.graph import END, StateGraph

from app.agents.chart_agent_state import ChartAgentState, DataRequirements
from app.schemas.chart import (
    ChartAgentAction,
    ChartAgentRequest,
    ChartAgentResponse,
    ChartData,
    ChartEncoding,
    ChartPatch,
    ChartSpec,
    ChartStyle,
    Intent,
)
from app.services.llm_actions import generate_llm_action
from app.services.metrics import get_metric_catalog, query_metrics, validate_data_access

QueryMetrics = Callable[[list[str], list[str], dict[str, Any] | None, dict[str, str] | None, int], ChartData]
LLMAction = Callable[[ChartAgentState], ChartAgentAction | None]


def run_chart_agent(request: ChartAgentRequest) -> ChartAgentResponse:
    graph = build_chart_agent_graph()
    initial_state: ChartAgentState = {
        "conversation_id": request.conversation_id,
        "user_message": request.message,
        "current_chart": request.current_chart,
        "page_context": request.page_context,
        "user_context": request.user_context,
        "data_requirements": None,
        "queried_data": None,
        "chart_action": None,
        "assistant_message": "",
        "errors": [],
    }
    final_state = graph.invoke(initial_state)
    action = final_state.get("chart_action") or ChartAgentAction(
        type="error",
        code="agent_no_action",
        message="Agent 未生成有效图表动作。",
    )
    return ChartAgentResponse(
        conversationId=request.conversation_id,
        intent=final_state.get("intent", "unknown"),
        action=action,
    )


def build_chart_agent_graph(
    query_metrics_fn: QueryMetrics = query_metrics,
    llm_action_fn: LLMAction = generate_llm_action,
):
    workflow = StateGraph(ChartAgentState)
    workflow.add_node("classify_intent", classify_intent_node)
    workflow.add_node("plan_data", plan_data_node)
    workflow.add_node("query_data", _make_query_data_node(query_metrics_fn))
    workflow.add_node("generate_action", _make_generate_action_node(llm_action_fn))
    workflow.add_node("validate_action", validate_action_node)
    workflow.add_node("respond", respond_node)

    workflow.set_entry_point("classify_intent")
    workflow.add_conditional_edges(
        "classify_intent",
        route_after_classification,
        {
            "plan_data": "plan_data",
            "generate_action": "generate_action",
        },
    )
    workflow.add_conditional_edges(
        "plan_data",
        route_after_planning,
        {
            "query_data": "query_data",
            "generate_action": "generate_action",
        },
    )
    workflow.add_edge("query_data", "generate_action")
    workflow.add_edge("generate_action", "validate_action")
    workflow.add_edge("validate_action", "respond")
    workflow.add_edge("respond", END)
    return workflow.compile()


def classify_intent_node(state: ChartAgentState) -> ChartAgentState:
    return {**state, "intent": classify_intent(state["user_message"])}


def classify_intent(message: str) -> Intent:
    normalized = message.strip().lower()
    if any(keyword in normalized for keyword in ["解释", "说明", "分析一下"]):
        return "explain_chart"
    if any(keyword in normalized for keyword in ["红色", "颜色", "蓝色", "绿色"]):
        return "update_style"
    if any(keyword in normalized for keyword in ["利润率", "订单数", "加一列", "新增指标"]):
        return "update_data"
    if any(keyword in normalized for keyword in ["折线", "柱状", "饼图", "表格", "换成"]):
        return "change_chart_type"
    if any(keyword in normalized for keyword in ["看", "生成", "统计", "销售额", "趋势"]):
        return "create_chart"
    return "unknown"


def route_after_classification(state: ChartAgentState) -> Literal["plan_data", "generate_action"]:
    return "plan_data" if state.get("intent") in {"create_chart", "update_data"} else "generate_action"


def plan_data_node(state: ChartAgentState) -> ChartAgentState:
    try:
        requirements = _resolve_data_requirements(state)
        get_metric_catalog(state["user_context"])
        validate_data_access(state["user_context"], requirements["metrics"], requirements["dimensions"])
        return {**state, "data_requirements": requirements}
    except ValueError as error:
        return _with_error(state, str(error))


def route_after_planning(state: ChartAgentState) -> Literal["query_data", "generate_action"]:
    return "generate_action" if state.get("errors") else "query_data"


def _make_query_data_node(query_metrics_fn: QueryMetrics):
    def query_data_node(state: ChartAgentState) -> ChartAgentState:
        requirements = state.get("data_requirements")
        if not requirements:
            return _with_error(state, "缺少数据查询需求。")
        data = query_metrics_fn(
            requirements["metrics"],
            requirements["dimensions"],
            requirements["filters"],
            requirements["time_range"],
            500,
        )
        return {**state, "queried_data": data}

    return query_data_node


def _make_generate_action_node(llm_action_fn: LLMAction):
    def generate_action_node(state: ChartAgentState) -> ChartAgentState:
        if state.get("errors"):
            return {**state, "chart_action": _error_action("validation_error", state["errors"][0])}

        try:
            llm_action = llm_action_fn(state)
        except Exception:
            llm_action = None
        if llm_action:
            return {**state, "chart_action": llm_action}

        intent = state.get("intent", "unknown")
        try:
            if intent == "create_chart":
                action = _create_chart_action(state)
            elif intent == "update_style":
                action = _update_style_action(state)
            elif intent == "update_data":
                action = _update_data_action(state)
            elif intent == "change_chart_type":
                action = _change_chart_type_action(state)
            elif intent == "explain_chart":
                action = _explain_chart_action(state)
            else:
                action = _error_action(
                    "clarification_required",
                    "我还不能确定你想创建还是修改图表，请明确指标、维度或修改目标。",
                )
        except ValueError as error:
            action = _error_action("validation_error", str(error))
        return {**state, "chart_action": action}

    return generate_action_node


def validate_action_node(state: ChartAgentState) -> ChartAgentState:
    action = state.get("chart_action")
    if not action:
        return {**state, "chart_action": _error_action("agent_no_action", "Agent 未生成有效图表动作。")}
    try:
        ChartAgentAction.model_validate(action.model_dump(by_alias=True))
        return state
    except ValueError as error:
        return {**state, "chart_action": _error_action("invalid_action", str(error))}


def respond_node(state: ChartAgentState) -> ChartAgentState:
    action = state.get("chart_action")
    return {**state, "assistant_message": action.message if action else ""}


def _resolve_data_requirements(state: ChartAgentState) -> DataRequirements:
    intent = state.get("intent", "unknown")
    message = state["user_message"]
    if intent == "create_chart":
        dimension = "date" if "趋势" in message or "折线" in message else "channel"
        return {"metrics": ["sales"], "dimensions": [dimension], "filters": {}, "time_range": None}

    if intent == "update_data":
        current = _require_current_chart(state)
        metrics = ["sales"]
        if "利润率" in message:
            metrics.append("profit_rate")
        if "订单数" in message:
            metrics.append("orders")
        dimension = current.encoding.x or current.encoding.category or "channel"
        return {"metrics": metrics, "dimensions": [dimension], "filters": {}, "time_range": None}

    raise ValueError("当前意图不需要数据查询。")


def _create_chart_action(state: ChartAgentState) -> ChartAgentAction:
    requirements = state.get("data_requirements")
    data = state.get("queried_data")
    if not requirements or not data:
        raise ValueError("创建图表缺少查询结果。")
    dimension = requirements["dimensions"][0]
    chart_type = "line" if dimension == "date" else "bar"
    chart = ChartSpec(
        id="chart_demo_sales",
        title="最近 30 天销售额",
        chartType=chart_type,
        data=data,
        encoding=ChartEncoding(x=dimension, y="sales"),
        style=ChartStyle(showLegend=False, showTooltip=True),
    )
    return ChartAgentAction(type="create_chart", chart=chart, message="已生成最近 30 天销售额图表。")


def _update_style_action(state: ChartAgentState) -> ChartAgentAction:
    current = _require_current_chart(state)
    color = "#ef4444"
    if "蓝色" in state["user_message"]:
        color = "#2563eb"
    if "绿色" in state["user_message"]:
        color = "#16a34a"
    colors = dict(current.style.colors or {})
    target = _resolve_style_target(state["user_message"], current)
    colors[target] = color
    return ChartAgentAction(
        type="update_chart",
        chartId=current.id,
        patch=ChartPatch(style=ChartStyle(colors=colors)),
        message=f"已将 {target} 调整为指定颜色。",
    )


def _update_data_action(state: ChartAgentState) -> ChartAgentAction:
    current = _require_current_chart(state)
    data = state.get("queried_data")
    if not data:
        raise ValueError("更新数据缺少查询结果。")
    visible_columns = [column.key for column in data.columns]
    return ChartAgentAction(
        type="update_chart",
        chartId=current.id,
        patch=ChartPatch(data=data, style=ChartStyle(visibleColumns=visible_columns)),
        message="已更新图表数据和指标列。",
    )


def _change_chart_type_action(state: ChartAgentState) -> ChartAgentAction:
    current = _require_current_chart(state)
    chart_type = _resolve_chart_type(state["user_message"])
    if chart_type == "pie":
        patch = ChartPatch(
            chartType="pie",
            encoding=ChartEncoding(
                category=current.encoding.x or current.encoding.category,
                value=current.encoding.y or current.encoding.value,
            ),
        )
    elif chart_type == "table":
        patch = ChartPatch(chartType="table")
    else:
        patch = ChartPatch(
            chartType=chart_type,
            encoding=ChartEncoding(
                x=current.encoding.x or current.encoding.category,
                y=current.encoding.y or current.encoding.value,
            ),
        )
    return ChartAgentAction(
        type="update_chart",
        chartId=current.id,
        patch=patch,
        message=f"已切换为{_chart_type_label(chart_type)}。",
    )


def _explain_chart_action(state: ChartAgentState) -> ChartAgentAction:
    current = _require_current_chart(state)
    rows_count = len(current.data.rows)
    columns = "、".join(column.label for column in current.data.columns)
    return _error_action("explanation", f"当前图表「{current.title}」包含 {rows_count} 行数据，字段包括：{columns}。")


def _require_current_chart(state: ChartAgentState) -> ChartSpec:
    current = state.get("current_chart")
    if not current:
        raise ValueError("当前没有可修改的图表，请先创建一个图表。")
    return current


def _resolve_style_target(message: str, chart: ChartSpec) -> str:
    for row in chart.data.rows:
        for value in row.values():
            if isinstance(value, str) and value in message:
                return value
    first_dimension = chart.encoding.x or chart.encoding.category
    if first_dimension and chart.data.rows:
        value = chart.data.rows[0].get(first_dimension)
        if isinstance(value, str):
            return value
    return "default"


def _resolve_chart_type(message: str) -> str:
    if "折线" in message:
        return "line"
    if "饼图" in message:
        return "pie"
    if "表格" in message:
        return "table"
    return "bar"


def _chart_type_label(chart_type: str) -> str:
    return {"bar": "柱状图", "line": "折线图", "pie": "饼图", "table": "表格"}[chart_type]


def _with_error(state: ChartAgentState, message: str) -> ChartAgentState:
    return {**state, "errors": [*state.get("errors", []), message]}


def _error_action(code: str, message: str) -> ChartAgentAction:
    return ChartAgentAction(type="error", code=code, message=message)
