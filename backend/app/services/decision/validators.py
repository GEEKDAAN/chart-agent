from app.schemas.agent_state import ChartAgentState
from app.domain.intents import (
    CURRENT_CHART_TOOLS,
    DETERMINISTIC_EDIT_TOOLS,
    TOOL_ANSWER_CURRENT_CHART_QUESTION,
    TOOL_CREATE_CHART,
    TOOL_TO_INTENT,
)
from app.schemas.chart import ChartAgentDecision

MIN_LLM_CONFIDENCE = 0.6


def is_usable_decision(
    decision: ChartAgentDecision,
    state: ChartAgentState,
    fallback_decision: ChartAgentDecision | None = None,
) -> bool:
    if decision.confidence < MIN_LLM_CONFIDENCE:
        return False
    if not _decision_intent_matches_tool(decision):
        return False
    if _conflicts_with_current_chart_question(decision, fallback_decision):
        return False
    if _conflicts_with_deterministic_create(decision, fallback_decision):
        return False
    if _conflicts_with_deterministic_edit(decision, fallback_decision):
        return False
    if decision.toolName in CURRENT_CHART_TOOLS:
        return bool(state.get("current_chart")) or decision.toolName == TOOL_ANSWER_CURRENT_CHART_QUESTION
    return True


def _conflicts_with_current_chart_question(
    decision: ChartAgentDecision,
    fallback_decision: ChartAgentDecision | None,
) -> bool:
    if not fallback_decision or fallback_decision.toolName != TOOL_ANSWER_CURRENT_CHART_QUESTION:
        return False
    return decision.toolName != TOOL_ANSWER_CURRENT_CHART_QUESTION


def _conflicts_with_deterministic_create(
    decision: ChartAgentDecision,
    fallback_decision: ChartAgentDecision | None,
) -> bool:
    if not fallback_decision or fallback_decision.toolName != TOOL_CREATE_CHART:
        return False
    return decision.toolName != TOOL_CREATE_CHART


def _conflicts_with_deterministic_edit(
    decision: ChartAgentDecision,
    fallback_decision: ChartAgentDecision | None,
) -> bool:
    if not fallback_decision or fallback_decision.toolName not in DETERMINISTIC_EDIT_TOOLS:
        return False
    return decision.toolName != fallback_decision.toolName


def _decision_intent_matches_tool(decision: ChartAgentDecision) -> bool:
    return TOOL_TO_INTENT[decision.toolName] == decision.intent
