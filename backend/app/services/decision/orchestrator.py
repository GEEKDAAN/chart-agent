from collections.abc import Callable

from app.schemas.agent_state import ChartAgentState
from app.schemas.chart import ChartAgentDecision
from app.services.decision.fallback import fallback_chart_agent_decision
from app.services.decision.llm import generate_llm_decision
from app.services.decision.validators import is_usable_decision

DecisionGenerator = Callable[[ChartAgentState], ChartAgentDecision | None]


def decide_chart_agent_tool(
    state: ChartAgentState,
    llm_decision_fn: DecisionGenerator = generate_llm_decision,
) -> ChartAgentDecision:
    fallback_decision = fallback_chart_agent_decision(state)
    llm_decision = llm_decision_fn(state)
    if llm_decision and is_usable_decision(llm_decision, state, fallback_decision):
        return llm_decision
    return fallback_decision
