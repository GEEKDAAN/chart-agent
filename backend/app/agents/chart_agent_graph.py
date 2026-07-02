from langgraph.graph import END, StateGraph

from app.agents.chart_agent_nodes import (
    DecisionFn,
    LLMAction,
    QueryMetrics,
    make_decide_tool_node,
    make_generate_action_node,
    make_query_data_node,
    plan_data_node,
    respond_node,
    route_after_classification,
    route_after_planning,
    validate_action_node,
)
from app.agents.chart_agent_state import ChartAgentState
from app.domain.actions import ACTION_ERROR, ERROR_CODE_AGENT_NO_ACTION
from app.domain.intents import INTENT_UNKNOWN
from app.schemas.chart import (
    ChartAgentAction,
    ChartAgentDecision,
    ChartAgentRequest,
    ChartAgentResponse,
    ChartSpec,
    Intent,
    UserContext,
)
from app.services.llm_actions import generate_llm_action
from app.services.llm_decisions import decide_chart_agent_tool, fallback_chart_agent_decision
from app.services.metrics import query_metrics


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
        uiBlocks=final_state.get("ui_blocks", []),
    )


def build_chart_agent_graph(
    query_metrics_fn: QueryMetrics = query_metrics,
    llm_action_fn: LLMAction = generate_llm_action,
    decision_fn: DecisionFn = decide_chart_agent_tool,
):
    workflow = StateGraph(ChartAgentState)
    workflow.add_node("decide_tool", make_decide_tool_node(decision_fn))
    workflow.add_node("plan_data", plan_data_node)
    workflow.add_node("query_data", make_query_data_node(query_metrics_fn))
    workflow.add_node("generate_action", make_generate_action_node(llm_action_fn))
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
