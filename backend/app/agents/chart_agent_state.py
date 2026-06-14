from typing import Any, NotRequired, TypedDict

from app.schemas.chart import ChartAgentAction, ChartAgentDecision, ChartData, ChartSpec, Intent, UserContext


class DataRequirements(TypedDict):
    metrics: list[str]
    dimensions: list[str]
    filters: dict[str, Any]
    time_range: dict[str, str] | None


class ChartAgentState(TypedDict):
    conversation_id: str
    user_message: str
    current_chart: ChartSpec | None
    page_context: dict[str, Any]
    user_context: UserContext
    intent: NotRequired[Intent]
    decision: NotRequired[ChartAgentDecision]
    data_requirements: NotRequired[DataRequirements | None]
    queried_data: NotRequired[ChartData | None]
    chart_action: NotRequired[ChartAgentAction | None]
    assistant_message: NotRequired[str]
    errors: NotRequired[list[str]]
