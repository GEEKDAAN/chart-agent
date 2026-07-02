from app.schemas.agent_state import ChartAgentState
from app.schemas.chart import ChartAgentDecision
from app.services.decision.chart_questions import answer_current_chart_question
from app.services.decision.fallback import fallback_chart_agent_decision
from app.services.decision.llm import generate_llm_decision as _generate_llm_decision
from app.services.decision.validators import MIN_LLM_CONFIDENCE, is_usable_decision


def decide_chart_agent_tool(state: ChartAgentState) -> ChartAgentDecision:
    fallback_decision = fallback_chart_agent_decision(state)
    llm_decision = _generate_llm_decision(state)
    if llm_decision and is_usable_decision(llm_decision, state, fallback_decision):
        return llm_decision
    return fallback_decision


__all__ = [
    "MIN_LLM_CONFIDENCE",
    "_generate_llm_decision",
    "answer_current_chart_question",
    "decide_chart_agent_tool",
    "fallback_chart_agent_decision",
    "is_usable_decision",
]
