from collections.abc import Callable
from typing import Any, Literal

from app.schemas.agent_state import ChartAgentState, DataRequirements
from app.domain.actions import (
    ERROR_CODE_AGENT_NO_ACTION,
    ERROR_CODE_CLARIFICATION_REQUIRED,
    ERROR_CODE_INVALID_ACTION,
    ERROR_CODE_VALIDATION_ERROR,
)
from app.domain.intents import (
    INTENT_CHANGE_CHART_TYPE,
    INTENT_CREATE_CHART,
    INTENT_EXPLAIN_CHART,
    INTENT_UNKNOWN,
    INTENT_UPDATE_DATA,
    INTENT_UPDATE_STYLE,
)
from app.schemas.chart import ChartAgentAction, ChartAgentDecision, ChartData
from app.services.action_errors import error_action, with_error
from app.services.chart_actions import (
    build_change_chart_type_action,
    build_conversational_action,
    build_create_chart_action,
    build_explain_chart_action,
    build_update_data_action,
    build_update_style_action,
)
from app.services.data_requirements import parse_data_requirements
from app.services.llm_decisions import fallback_chart_agent_decision
from app.services.metrics import get_metric_catalog, validate_data_access
from app.services.ui_blocks import build_chart_ui_blocks

QueryMetrics = Callable[[list[str], list[str], dict[str, Any] | None, dict[str, str] | None, int], ChartData]
LLMAction = Callable[[ChartAgentState], ChartAgentAction | None]
DecisionFn = Callable[[ChartAgentState], ChartAgentDecision]


def make_decide_tool_node(decision_fn: DecisionFn):
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


def route_after_classification(state: ChartAgentState) -> Literal["plan_data", "generate_action"]:
    return "plan_data" if state.get("intent") in {INTENT_CREATE_CHART, INTENT_UPDATE_DATA} else "generate_action"


def plan_data_node(state: ChartAgentState) -> ChartAgentState:
    try:
        requirements = _resolve_data_requirements(state)
        get_metric_catalog(state["user_context"])
        validate_data_access(state["user_context"], requirements["metrics"], requirements["dimensions"])
        return {**state, "data_requirements": requirements}
    except ValueError as error:
        return with_error(state, str(error))


def route_after_planning(state: ChartAgentState) -> Literal["query_data", "generate_action"]:
    return "generate_action" if state.get("errors") else "query_data"


def make_query_data_node(query_metrics_fn: QueryMetrics):
    def query_data_node(state: ChartAgentState) -> ChartAgentState:
        requirements = state.get("data_requirements")
        if not requirements:
            return with_error(state, "缺少数据查询需求。")
        data = query_metrics_fn(
            requirements["metrics"],
            requirements["dimensions"],
            requirements["filters"],
            requirements["time_range"],
            500,
        )
        return {**state, "queried_data": data}

    return query_data_node


def make_generate_action_node(llm_action_fn: LLMAction):
    def generate_action_node(state: ChartAgentState) -> ChartAgentState:
        if state.get("errors"):
            return {**state, "chart_action": error_action(ERROR_CODE_VALIDATION_ERROR, state["errors"][0])}

        conversational_action = build_conversational_action(state.get("intent", INTENT_UNKNOWN))
        if conversational_action:
            return {**state, "chart_action": conversational_action}

        if state.get("intent") == INTENT_EXPLAIN_CHART and state.get("current_chart"):
            return {**state, "chart_action": build_explain_chart_action(state)}

        if state.get("intent") == INTENT_UPDATE_STYLE:
            try:
                return {**state, "chart_action": build_update_style_action(state)}
            except ValueError as error:
                return {**state, "chart_action": error_action(ERROR_CODE_VALIDATION_ERROR, str(error))}

        try:
            llm_action = llm_action_fn(state)
        except Exception:
            llm_action = None
        if llm_action:
            return {**state, "chart_action": llm_action}

        intent = state.get("intent", INTENT_UNKNOWN)
        try:
            if intent == INTENT_CREATE_CHART:
                action = build_create_chart_action(state)
            elif intent == INTENT_UPDATE_STYLE:
                action = build_update_style_action(state)
            elif intent == INTENT_UPDATE_DATA:
                action = build_update_data_action(state)
            elif intent == INTENT_CHANGE_CHART_TYPE:
                action = build_change_chart_type_action(state)
            elif intent == INTENT_EXPLAIN_CHART:
                action = build_explain_chart_action(state)
            else:
                action = error_action(
                    ERROR_CODE_CLARIFICATION_REQUIRED,
                    "我还不能确定你想创建还是修改图表，请明确指标、维度或修改目标。",
                )
        except ValueError as error:
            action = error_action(ERROR_CODE_VALIDATION_ERROR, str(error))
        return {**state, "chart_action": action}

    return generate_action_node


def validate_action_node(state: ChartAgentState) -> ChartAgentState:
    action = state.get("chart_action")
    if not action:
        return {**state, "chart_action": error_action(ERROR_CODE_AGENT_NO_ACTION, "Agent 未生成有效图表动作。")}
    try:
        ChartAgentAction.model_validate(action.model_dump(by_alias=True))
        return state
    except ValueError as error:
        return {**state, "chart_action": error_action(ERROR_CODE_INVALID_ACTION, str(error))}


def respond_node(state: ChartAgentState) -> ChartAgentState:
    action = state.get("chart_action")
    ui_blocks = build_chart_ui_blocks(action) if action else []
    return {**state, "assistant_message": action.message if action else "", "ui_blocks": ui_blocks}


def _resolve_data_requirements(state: ChartAgentState) -> DataRequirements:
    return parse_data_requirements(
        message=state["user_message"],
        intent=state.get("intent", INTENT_UNKNOWN),
        current_chart=state.get("current_chart"),
    )
