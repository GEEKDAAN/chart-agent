from collections.abc import Callable
from typing import Any, Literal

from langgraph.graph import END, StateGraph

from app.agents.chart_agent_state import ChartAgentState, DataRequirements
from app.domain.actions import (
    ACTION_CREATE_CHART,
    ACTION_ERROR,
    ACTION_UPDATE_CHART,
    ERROR_CODE_AGENT_NO_ACTION,
    ERROR_CODE_CLARIFICATION_REQUIRED,
    ERROR_CODE_EXPLANATION,
    ERROR_CODE_HELP,
    ERROR_CODE_INVALID_ACTION,
    ERROR_CODE_OUT_OF_SCOPE,
    ERROR_CODE_SMALLTALK,
    ERROR_CODE_VALIDATION_ERROR,
)
from app.domain.chart_types import (
    CHART_TYPE_BAR,
    CHART_TYPE_LABELS,
    CHART_TYPE_LINE,
    CHART_TYPE_PIE,
    CHART_TYPE_TABLE,
)
from app.domain.dimensions import DIMENSION_DATE, DIMENSION_LABELS
from app.domain.intents import (
    INTENT_CHANGE_CHART_TYPE,
    INTENT_CREATE_CHART,
    INTENT_EXPLAIN_CHART,
    INTENT_HELP,
    INTENT_OUT_OF_SCOPE,
    INTENT_SMALLTALK,
    INTENT_UNCLEAR_CHART_REQUEST,
    INTENT_UNKNOWN,
    INTENT_UPDATE_DATA,
    INTENT_UPDATE_STYLE,
)
from app.domain.metrics import METRIC_LABELS
from app.domain.visibility import VISIBILITY_HIDE
from app.schemas.chart import (
    ChartAgentAction,
    ChartAgentDecision,
    ChartAgentRequest,
    ChartAgentResponse,
    ChartData,
    ChartEncoding,
    ChartPatch,
    ChartSpec,
    ChartStyle,
    Intent,
    UserContext,
)
from app.services.llm_actions import generate_llm_action
from app.services.llm_decisions import (
    answer_current_chart_question,
    decide_chart_agent_tool,
    fallback_chart_agent_decision,
)
from app.services.data_requirements import parse_data_requirements
from app.services.metrics import get_metric_catalog, query_metrics, validate_data_access
from app.services.style_updates import color_label, resolve_style_updates
from app.services.visibility_updates import VisibilityUpdate, resolve_visibility_update

QueryMetrics = Callable[[list[str], list[str], dict[str, Any] | None, dict[str, str] | None, int], ChartData]
LLMAction = Callable[[ChartAgentState], ChartAgentAction | None]
DecisionFn = Callable[[ChartAgentState], ChartAgentDecision]


def run_chart_agent(request: ChartAgentRequest, initial_decision: ChartAgentDecision | None = None) -> ChartAgentResponse:
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
    if initial_decision:
        initial_state["decision"] = initial_decision
    final_state = graph.invoke(initial_state)
    action = final_state.get("chart_action") or ChartAgentAction(
        type=ACTION_ERROR,
        code=ERROR_CODE_AGENT_NO_ACTION,
        message="Agent 未生成有效图表动作。",
    )
    return ChartAgentResponse(
        conversationId=request.conversation_id,
        intent=final_state.get("intent", INTENT_UNKNOWN),
        action=action,
    )


def build_chart_agent_graph(
    query_metrics_fn: QueryMetrics = query_metrics,
    llm_action_fn: LLMAction = generate_llm_action,
    decision_fn: DecisionFn = decide_chart_agent_tool,
):
    workflow = StateGraph(ChartAgentState)
    workflow.add_node("decide_tool", _make_decide_tool_node(decision_fn))
    workflow.add_node("plan_data", plan_data_node)
    workflow.add_node("query_data", _make_query_data_node(query_metrics_fn))
    workflow.add_node("generate_action", _make_generate_action_node(llm_action_fn))
    workflow.add_node("validate_action", validate_action_node)
    workflow.add_node("respond", respond_node)

    workflow.set_entry_point("decide_tool")
    workflow.add_conditional_edges(
        "decide_tool",
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


def _make_decide_tool_node(decision_fn: DecisionFn):
    def decide_tool_node(state: ChartAgentState) -> ChartAgentState:
        if state.get("decision"):
            decision = state["decision"]
            return {**state, "intent": decision.intent}
        try:
            decision = decision_fn(state)
        except Exception:
            decision = fallback_chart_agent_decision(state)
        return {**state, "decision": decision, "intent": decision.intent}

    return decide_tool_node


def classify_intent(message: str, current_chart: ChartSpec | None = None) -> Intent:
    state: ChartAgentState = {
        "conversation_id": "compat",
        "user_message": message,
        "current_chart": current_chart,
        "page_context": {},
        "user_context": UserContext(userId="compat", tenantId="demo"),
        "data_requirements": None,
        "queried_data": None,
        "chart_action": None,
        "assistant_message": "",
        "errors": [],
    }
    return fallback_chart_agent_decision(state).intent


def route_after_classification(state: ChartAgentState) -> Literal["plan_data", "generate_action"]:
    return "plan_data" if state.get("intent") in {INTENT_CREATE_CHART, INTENT_UPDATE_DATA} else "generate_action"


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
            return {**state, "chart_action": _error_action(ERROR_CODE_VALIDATION_ERROR, state["errors"][0])}

        conversational_action = _conversational_action(state.get("intent", INTENT_UNKNOWN))
        if conversational_action:
            return {**state, "chart_action": conversational_action}

        if state.get("intent") == INTENT_EXPLAIN_CHART and state.get("current_chart"):
            return {**state, "chart_action": _explain_chart_action(state)}

        if state.get("intent") == INTENT_UPDATE_STYLE:
            try:
                return {**state, "chart_action": _update_style_action(state)}
            except ValueError as error:
                return {**state, "chart_action": _error_action(ERROR_CODE_VALIDATION_ERROR, str(error))}

        try:
            llm_action = llm_action_fn(state)
        except Exception:
            llm_action = None
        if llm_action:
            return {**state, "chart_action": llm_action}

        intent = state.get("intent", INTENT_UNKNOWN)
        try:
            if intent == INTENT_CREATE_CHART:
                action = _create_chart_action(state)
            elif intent == INTENT_UPDATE_STYLE:
                action = _update_style_action(state)
            elif intent == INTENT_UPDATE_DATA:
                action = _update_data_action(state)
            elif intent == INTENT_CHANGE_CHART_TYPE:
                action = _change_chart_type_action(state)
            elif intent == INTENT_EXPLAIN_CHART:
                action = _explain_chart_action(state)
            else:
                action = _error_action(
                    ERROR_CODE_CLARIFICATION_REQUIRED,
                    "我还不能确定你想创建还是修改图表，请明确指标、维度或修改目标。",
                )
        except ValueError as error:
            action = _error_action(ERROR_CODE_VALIDATION_ERROR, str(error))
        return {**state, "chart_action": action}

    return generate_action_node


def _conversational_action(intent: Intent) -> ChartAgentAction | None:
    if intent == INTENT_SMALLTALK:
        return _error_action(
            ERROR_CODE_SMALLTALK,
            "你好，我是 chart-agent。你可以告诉我想看什么指标、按什么维度分析，或者让我修改当前图表。",
        )
    if intent == INTENT_HELP:
        return _error_action(
            ERROR_CODE_HELP,
            "我可以生成图表、修改图表颜色、切换图表类型、增加指标列，并解释当前图表。比如：看最近30天各渠道销售额、把抖音改成红色、换成折线图。",
        )
    if intent == INTENT_OUT_OF_SCOPE:
        return _error_action(
            ERROR_CODE_OUT_OF_SCOPE,
            "我目前只处理图表生成、图表编辑和图表解释相关需求。请告诉我你想分析的指标、维度或要修改的图表内容。",
        )
    if intent == INTENT_UNCLEAR_CHART_REQUEST:
        return _error_action(
            ERROR_CODE_CLARIFICATION_REQUIRED,
            "我还不能确定你的图表需求。请明确指标、维度或修改目标，例如“看最近30天各渠道销售额”或“把抖音改成红色”。",
        )
    return None


def validate_action_node(state: ChartAgentState) -> ChartAgentState:
    action = state.get("chart_action")
    if not action:
        return {**state, "chart_action": _error_action(ERROR_CODE_AGENT_NO_ACTION, "Agent 未生成有效图表动作。")}
    try:
        ChartAgentAction.model_validate(action.model_dump(by_alias=True))
        return state
    except ValueError as error:
        return {**state, "chart_action": _error_action(ERROR_CODE_INVALID_ACTION, str(error))}


def respond_node(state: ChartAgentState) -> ChartAgentState:
    action = state.get("chart_action")
    return {**state, "assistant_message": action.message if action else ""}


def _resolve_data_requirements(state: ChartAgentState) -> DataRequirements:
    return parse_data_requirements(
        message=state["user_message"],
        intent=state.get("intent", INTENT_UNKNOWN),
        current_chart=state.get("current_chart"),
    )


def _create_chart_action(state: ChartAgentState) -> ChartAgentAction:
    requirements = state.get("data_requirements")
    data = state.get("queried_data")
    if not requirements or not data:
        raise ValueError("创建图表缺少查询结果。")
    dimension = requirements["dimensions"][0]
    metric = requirements["metrics"][0]
    chart_type = CHART_TYPE_LINE if dimension == DIMENSION_DATE else CHART_TYPE_BAR
    metric_label = _metric_label(metric)
    chart = ChartSpec(
        id=f"chart_demo_{metric}",
        title=f"{_dimension_label(dimension)}{metric_label}",
        chartType=chart_type,
        data=data,
        encoding=ChartEncoding(x=dimension, y=metric),
        style=ChartStyle(showLegend=False, showTooltip=True),
    )
    return ChartAgentAction(type=ACTION_CREATE_CHART, chart=chart, message=f"已生成{metric_label}图表。")


def _update_style_action(state: ChartAgentState) -> ChartAgentAction:
    current = _require_current_chart(state)
    colors = dict(current.style.colors or {})
    hidden_values = dict(current.style.hiddenValues or {})
    updates: dict[str, str] = {}
    visibility_update = resolve_visibility_update(state, current)

    try:
        updates = resolve_style_updates(state, current)
    except ValueError:
        if not visibility_update:
            raise

    colors.update(updates)
    if visibility_update:
        hidden_values = visibility_update.hidden_values

    change_parts = []
    if updates:
        change_parts.append("，".join(f"{target} 调整为{color_label(color)}" for target, color in updates.items()))
    if visibility_update:
        change_parts.append(_visibility_change_text(visibility_update))

    if not change_parts:
        raise ValueError("未识别到要修改的图表样式。")

    return ChartAgentAction(
        type=ACTION_UPDATE_CHART,
        chartId=current.id,
        patch=ChartPatch(style=ChartStyle(colors=colors, hiddenValues=hidden_values)),
        message=f"已将 {'；'.join(change_parts)}。",
    )


def _visibility_change_text(update: VisibilityUpdate) -> str:
    target_text = "、".join(update.targets)
    if update.action == VISIBILITY_HIDE:
        return f"{update.dimension_label}「{target_text}」隐藏"
    return f"{update.dimension_label}「{target_text}」恢复显示"


def _update_data_action(state: ChartAgentState) -> ChartAgentAction:
    current = _require_current_chart(state)
    data = state.get("queried_data")
    if not data:
        raise ValueError("更新数据缺少查询结果。")
    visible_columns = [column.key for column in data.columns]
    return ChartAgentAction(
        type=ACTION_UPDATE_CHART,
        chartId=current.id,
        patch=ChartPatch(data=data, style=ChartStyle(visibleColumns=visible_columns)),
        message="已更新图表数据和指标列。",
    )


def _change_chart_type_action(state: ChartAgentState) -> ChartAgentAction:
    current = _require_current_chart(state)
    chart_type = _resolve_chart_type(state["user_message"])
    if chart_type == CHART_TYPE_PIE:
        patch = ChartPatch(
            chartType=CHART_TYPE_PIE,
            encoding=ChartEncoding(
                category=current.encoding.x or current.encoding.category,
                value=current.encoding.y or current.encoding.value,
            ),
        )
    elif chart_type == CHART_TYPE_TABLE:
        patch = ChartPatch(chartType=CHART_TYPE_TABLE)
    else:
        patch = ChartPatch(
            chartType=chart_type,
            encoding=ChartEncoding(
                x=current.encoding.x or current.encoding.category,
                y=current.encoding.y or current.encoding.value,
            ),
        )
    return ChartAgentAction(
        type=ACTION_UPDATE_CHART,
        chartId=current.id,
        patch=patch,
        message=f"已切换为{_chart_type_label(chart_type)}。",
    )


def _explain_chart_action(state: ChartAgentState) -> ChartAgentAction:
    current = _require_current_chart(state)
    return _error_action(ERROR_CODE_EXPLANATION, answer_current_chart_question(state["user_message"], current))


def _require_current_chart(state: ChartAgentState) -> ChartSpec:
    current = state.get("current_chart")
    if not current:
        raise ValueError("当前没有可修改的图表，请先创建一个图表。")
    return current


def _resolve_chart_type(message: str) -> str:
    if "折线" in message:
        return CHART_TYPE_LINE
    if "饼图" in message:
        return CHART_TYPE_PIE
    if "表格" in message:
        return CHART_TYPE_TABLE
    return CHART_TYPE_BAR


def _chart_type_label(chart_type: str) -> str:
    return CHART_TYPE_LABELS[chart_type]


def _metric_label(metric: str) -> str:
    return METRIC_LABELS.get(metric, metric)


def _dimension_label(dimension: str) -> str:
    return DIMENSION_LABELS.get(dimension, "")


def _with_error(state: ChartAgentState, message: str) -> ChartAgentState:
    return {**state, "errors": [*state.get("errors", []), message]}


def _error_action(code: str, message: str) -> ChartAgentAction:
    return ChartAgentAction(type=ACTION_ERROR, code=code, message=message)
