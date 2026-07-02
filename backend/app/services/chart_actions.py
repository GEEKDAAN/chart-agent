from app.agents.chart_agent_state import ChartAgentState
from app.domain.actions import (
    ACTION_CREATE_CHART,
    ACTION_UPDATE_CHART,
    ERROR_CODE_CLARIFICATION_REQUIRED,
    ERROR_CODE_EXPLANATION,
    ERROR_CODE_HELP,
    ERROR_CODE_OUT_OF_SCOPE,
    ERROR_CODE_SMALLTALK,
)
from app.domain.chart_types import (
    CHART_TYPE_BAR,
    CHART_TYPE_LABELS,
    CHART_TYPE_LINE,
    CHART_TYPE_PIE,
    CHART_TYPE_TABLE,
)
from app.domain.dimensions import DIMENSION_DATE, DIMENSION_LABELS
from app.domain.intents import (
    INTENT_HELP,
    INTENT_OUT_OF_SCOPE,
    INTENT_SMALLTALK,
    INTENT_UNCLEAR_CHART_REQUEST,
)
from app.domain.metrics import METRIC_LABELS
from app.domain.visibility import VISIBILITY_HIDE
from app.schemas.chart import ChartAgentAction, ChartEncoding, ChartPatch, ChartSpec, ChartStyle, Intent
from app.services.action_errors import error_action
from app.services.llm_decisions import answer_current_chart_question
from app.services.style_updates import color_label, resolve_style_updates
from app.services.visibility_updates import VisibilityUpdate, resolve_visibility_update


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
    metric_label = _metric_label(metric)
    chart = ChartSpec(
        id=f"chart_demo_{metric}",
        title=f"{_dimension_label(dimension)}{metric_label}",
        chartType=chart_type,
        data=data,
        encoding=ChartEncoding(x=dimension, y=metric),
        style=ChartStyle(showLegend=False, showTooltip=True),
    )
    return ChartAgentAction(type=ACTION_CREATE_CHART, chart=chart, message=f"已生成{metric_label}图表。")


def build_update_style_action(state: ChartAgentState) -> ChartAgentAction:
    current = _require_current_chart(state)
    colors = dict(current.style.colors or {})
    hidden_values = dict(current.style.hiddenValues or {})
    updates: dict[str, str] = {}
    visibility_update = resolve_visibility_update(state, current)

    try:
        updates = resolve_style_updates(state, current)
    except ValueError:
        if not visibility_update:
            raise

    colors.update(updates)
    if visibility_update:
        hidden_values = visibility_update.hidden_values

    change_parts = []
    if updates:
        change_parts.append("，".join(f"{target} 调整为{color_label(color)}" for target, color in updates.items()))
    if visibility_update:
        change_parts.append(_visibility_change_text(visibility_update))

    if not change_parts:
        raise ValueError("未识别到要修改的图表样式。")

    return ChartAgentAction(
        type=ACTION_UPDATE_CHART,
        chartId=current.id,
        patch=ChartPatch(style=ChartStyle(colors=colors, hiddenValues=hidden_values)),
        message=f"已将 {'；'.join(change_parts)}。",
    )


def build_update_data_action(state: ChartAgentState) -> ChartAgentAction:
    current = _require_current_chart(state)
    data = state.get("queried_data")
    if not data:
        raise ValueError("更新数据缺少查询结果。")
    visible_columns = [column.key for column in data.columns]
    return ChartAgentAction(
        type=ACTION_UPDATE_CHART,
        chartId=current.id,
        patch=ChartPatch(data=data, style=ChartStyle(visibleColumns=visible_columns)),
        message="已更新图表数据和指标列。",
    )


def build_change_chart_type_action(state: ChartAgentState) -> ChartAgentAction:
    current = _require_current_chart(state)
    chart_type = _resolve_chart_type(state["user_message"])
    if chart_type == CHART_TYPE_PIE:
        patch = ChartPatch(
            chartType=CHART_TYPE_PIE,
            encoding=ChartEncoding(
                category=current.encoding.x or current.encoding.category,
                value=current.encoding.y or current.encoding.value,
            ),
        )
    elif chart_type == CHART_TYPE_TABLE:
        patch = ChartPatch(chartType=CHART_TYPE_TABLE)
    else:
        patch = ChartPatch(
            chartType=chart_type,
            encoding=ChartEncoding(
                x=current.encoding.x or current.encoding.category,
                y=current.encoding.y or current.encoding.value,
            ),
        )
    return ChartAgentAction(
        type=ACTION_UPDATE_CHART,
        chartId=current.id,
        patch=patch,
        message=f"已切换为{_chart_type_label(chart_type)}。",
    )


def build_explain_chart_action(state: ChartAgentState) -> ChartAgentAction:
    current = _require_current_chart(state)
    return error_action(ERROR_CODE_EXPLANATION, answer_current_chart_question(state["user_message"], current))


def _visibility_change_text(update: VisibilityUpdate) -> str:
    target_text = "、".join(update.targets)
    if update.action == VISIBILITY_HIDE:
        return f"{update.dimension_label}「{target_text}」隐藏"
    return f"{update.dimension_label}「{target_text}」恢复显示"


def _require_current_chart(state: ChartAgentState) -> ChartSpec:
    current = state.get("current_chart")
    if not current:
        raise ValueError("当前没有可修改的图表，请先创建一个图表。")
    return current


def _resolve_chart_type(message: str) -> str:
    if "折线" in message:
        return CHART_TYPE_LINE
    if "饼图" in message:
        return CHART_TYPE_PIE
    if "表格" in message:
        return CHART_TYPE_TABLE
    return CHART_TYPE_BAR


def _chart_type_label(chart_type: str) -> str:
    return CHART_TYPE_LABELS[chart_type]


def _metric_label(metric: str) -> str:
    return METRIC_LABELS.get(metric, metric)


def _dimension_label(dimension: str) -> str:
    return DIMENSION_LABELS.get(dimension, "")
