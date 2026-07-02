from app.domain.actions import ACTION_UPDATE_CHART
from app.domain.chart_types import CHART_TYPE_PIE, CHART_TYPE_TABLE
from app.domain.visibility import VISIBILITY_HIDE
from app.schemas.agent_state import ChartAgentState
from app.schemas.chart import ChartAgentAction, ChartEncoding, ChartPatch, ChartStyle
from app.services.chart_action_helpers import chart_type_label, require_current_chart, resolve_chart_type
from app.services.style_updates import color_label, resolve_style_updates
from app.services.visibility_updates import VisibilityUpdate, resolve_visibility_update


def build_update_style_action(state: ChartAgentState) -> ChartAgentAction:
    current = require_current_chart(state)
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
    current = require_current_chart(state)
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
    current = require_current_chart(state)
    chart_type = resolve_chart_type(state["user_message"])
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
        message=f"已切换为{chart_type_label(chart_type)}。",
    )


def _visibility_change_text(update: VisibilityUpdate) -> str:
    target_text = "、".join(update.targets)
    if update.action == VISIBILITY_HIDE:
        return f"{update.dimension_label}「{target_text}」隐藏"
    return f"{update.dimension_label}「{target_text}」恢复显示"
