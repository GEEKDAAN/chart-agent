from app.agents.chart_agent_state import ChartAgentState
from app.domain.actions import ACTION_ERROR
from app.schemas.chart import ChartAgentAction


def with_error(state: ChartAgentState, message: str) -> ChartAgentState:
    return {**state, "errors": [*state.get("errors", []), message]}


def error_action(code: str, message: str) -> ChartAgentAction:
    return ChartAgentAction(type=ACTION_ERROR, code=code, message=message)
