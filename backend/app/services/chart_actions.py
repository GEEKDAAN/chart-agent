from app.domain.actions import (
    ACTION_CREATE_CHART,
    ERROR_CODE_CLARIFICATION_REQUIRED,
    ERROR_CODE_HELP,
    ERROR_CODE_OUT_OF_SCOPE,
    ERROR_CODE_SMALLTALK,
)
from app.domain.chart_types import CHART_TYPE_BAR, CHART_TYPE_LINE
from app.domain.dimensions import DIMENSION_DATE
from app.domain.intents import (
    INTENT_HELP,
    INTENT_OUT_OF_SCOPE,
    INTENT_SMALLTALK,
    INTENT_UNCLEAR_CHART_REQUEST,
)
from app.schemas.agent_state import ChartAgentState
from app.schemas.chart import ChartAgentAction, ChartEncoding, ChartSpec, ChartStyle, Intent
from app.services.action_errors import error_action
from app.services.chart_action_helpers import dimension_label, metric_label


def build_conversational_action(intent: Intent) -> ChartAgentAction | None:
    if intent == INTENT_SMALLTALK:
        return error_action(
            ERROR_CODE_SMALLTALK,
            "你好，我是 chart-agent。你可以告诉我想看什么指标、按什么维度分析，或者让我修改当前图表。",
        )
    if intent == INTENT_HELP:
        return error_action(
            ERROR_CODE_HELP,
            "我可以生成图表、修改图表颜色、切换图表类型、增加指标列，并解释当前图表。比如：看最近30天各渠道销售额、把抖音改成红色、换成折线图。",
        )
    if intent == INTENT_OUT_OF_SCOPE:
        return error_action(
            ERROR_CODE_OUT_OF_SCOPE,
            "我目前只处理图表生成、图表编辑和图表解释相关需求。请告诉我你想分析的指标、维度或要修改的图表内容。",
        )
    if intent == INTENT_UNCLEAR_CHART_REQUEST:
        return error_action(
            ERROR_CODE_CLARIFICATION_REQUIRED,
            "我还不能确定你的图表需求。请明确指标、维度或修改目标，例如“看最近30天各渠道销售额”或“把抖音改成红色”。",
        )
    return None


def build_create_chart_action(state: ChartAgentState) -> ChartAgentAction:
    requirements = state.get("data_requirements")
    data = state.get("queried_data")
    if not requirements or not data:
        raise ValueError("创建图表缺少查询结果。")
    dimension = requirements["dimensions"][0]
    metric = requirements["metrics"][0]
    chart_type = CHART_TYPE_LINE if dimension == DIMENSION_DATE else CHART_TYPE_BAR
    label = metric_label(metric)
    chart = ChartSpec(
        id=f"chart_demo_{metric}",
        title=f"{dimension_label(dimension)}{label}",
        chartType=chart_type,
        data=data,
        encoding=ChartEncoding(x=dimension, y=metric),
        style=ChartStyle(showLegend=False, showTooltip=True),
    )
    return ChartAgentAction(type=ACTION_CREATE_CHART, chart=chart, message=f"已生成{label}图表。")
