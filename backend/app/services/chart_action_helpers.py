from app.domain.chart_types import CHART_TYPE_BAR, CHART_TYPE_LABELS, CHART_TYPE_LINE, CHART_TYPE_PIE, CHART_TYPE_TABLE
from app.domain.dimensions import DIMENSION_LABELS
from app.domain.metrics import METRIC_LABELS
from app.schemas.agent_state import ChartAgentState
from app.schemas.chart import ChartSpec


def require_current_chart(state: ChartAgentState) -> ChartSpec:
    current = state.get("current_chart")
    if not current:
        raise ValueError("当前没有可修改的图表，请先创建一个图表。")
    return current


def resolve_chart_type(message: str) -> str:
    if "折线" in message:
        return CHART_TYPE_LINE
    if "饼图" in message:
        return CHART_TYPE_PIE
    if "表格" in message:
        return CHART_TYPE_TABLE
    return CHART_TYPE_BAR


def chart_type_label(chart_type: str) -> str:
    return CHART_TYPE_LABELS[chart_type]


def metric_label(metric: str) -> str:
    return METRIC_LABELS.get(metric, metric)


def dimension_label(dimension: str) -> str:
    return DIMENSION_LABELS.get(dimension, "")
