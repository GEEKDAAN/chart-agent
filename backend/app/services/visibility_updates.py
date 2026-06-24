from dataclasses import dataclass
from typing import Literal

from app.agents.chart_agent_state import ChartAgentState
from app.schemas.chart import ChartSpec

VisibilityAction = Literal["hide", "show"]


@dataclass(frozen=True)
class VisibilityUpdate:
    action: VisibilityAction
    hidden_values: dict[str, list[str]]
    targets: list[str]
    dimension_key: str
    dimension_label: str


def resolve_visibility_update(state: ChartAgentState, chart: ChartSpec) -> VisibilityUpdate | None:
    message = state["user_message"]
    action = _resolve_visibility_action(message)
    if not action:
        return None

    dimension_key = _resolve_dimension_key(chart)
    if not dimension_key:
        return None

    targets = _targets_in_message(message, chart, dimension_key)
    if not targets and action == "show" and any(keyword in message for keyword in ["全部", "所有"]):
        targets = _hidden_values(chart, dimension_key)
    if not targets:
        return None

    hidden_values = {key: list(values) for key, values in (chart.style.hiddenValues or {}).items()}
    current_values = hidden_values.get(dimension_key, [])

    if action == "hide":
        next_values = [*current_values]
        for target in targets:
            if target not in next_values:
                next_values.append(target)
        hidden_values[dimension_key] = next_values
    else:
        next_values = [value for value in current_values if value not in targets]
        if next_values:
            hidden_values[dimension_key] = next_values
        else:
            hidden_values.pop(dimension_key, None)

    return VisibilityUpdate(
        action=action,
        hidden_values=hidden_values,
        targets=targets,
        dimension_key=dimension_key,
        dimension_label=_column_label(chart, dimension_key),
    )


def looks_like_visibility_update(message: str, chart: ChartSpec) -> bool:
    if not _resolve_visibility_action(message):
        return False
    dimension_key = _resolve_dimension_key(chart)
    return bool(dimension_key and _targets_in_message(message, chart, dimension_key))


def _resolve_visibility_action(message: str) -> VisibilityAction | None:
    hide_terms = ["不要显示", "不显示", "隐藏", "去掉", "移除", "删掉", "删除", "过滤掉", "排除"]
    show_terms = ["恢复显示", "取消隐藏", "显示回来", "重新显示", "显示", "展示"]
    if any(term in message for term in hide_terms):
        return "hide"
    if any(term in message for term in show_terms):
        return "show"
    return None


def _resolve_dimension_key(chart: ChartSpec) -> str | None:
    if chart.encoding.x:
        return chart.encoding.x
    if chart.encoding.category:
        return chart.encoding.category
    for column in chart.data.columns:
        if column.type == "string":
            return column.key
    return None


def _targets_in_message(message: str, chart: ChartSpec, dimension_key: str) -> list[str]:
    targets: list[str] = []
    for row in chart.data.rows:
        value = row.get(dimension_key)
        if isinstance(value, str) and value in message and value not in targets:
            targets.append(value)
    return targets


def _hidden_values(chart: ChartSpec, dimension_key: str) -> list[str]:
    return list((chart.style.hiddenValues or {}).get(dimension_key, []))


def _column_label(chart: ChartSpec, key: str) -> str:
    for column in chart.data.columns:
        if column.key == key:
            return column.label
    return key
