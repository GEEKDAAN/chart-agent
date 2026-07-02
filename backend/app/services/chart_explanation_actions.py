from app.domain.actions import ERROR_CODE_EXPLANATION
from app.schemas.agent_state import ChartAgentState
from app.schemas.chart import ChartAgentAction
from app.services.action_errors import error_action
from app.services.chart_action_helpers import require_current_chart
from app.services.llm_decisions import answer_current_chart_question


def build_explain_chart_action(state: ChartAgentState) -> ChartAgentAction:
    current = require_current_chart(state)
    return error_action(ERROR_CODE_EXPLANATION, answer_current_chart_question(state["user_message"], current))
