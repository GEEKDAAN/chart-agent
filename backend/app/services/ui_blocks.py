from typing import Any

from app.domain.actions import ACTION_CREATE_CHART
from app.domain.chart_types import CHART_TYPE_BAR, CHART_TYPE_LINE
from app.domain.column_types import COLUMN_TYPE_CURRENCY, COLUMN_TYPE_NUMBER, COLUMN_TYPE_PERCENT
from app.domain.dimensions import DIMENSION_CHANNEL
from app.domain.ui_blocks import (
    UI_BLOCK_DATA_TABLE,
    UI_BLOCK_INSIGHT_CARD,
    UI_BLOCK_METRIC_SUMMARY,
    UI_BLOCK_SUGGESTED_ACTIONS,
)
from app.schemas.chart import ChartAgentAction, ChartAgentUiBlock, ChartColumn, ChartSpec


def build_chart_ui_blocks(action: ChartAgentAction) -> list[ChartAgentUiBlock]:
    if action.type != ACTION_CREATE_CHART or action.chart is None:
        return []
    return build_create_chart_ui_blocks(action.chart)


def build_create_chart_ui_blocks(chart: ChartSpec) -> list[ChartAgentUiBlock]:
    dimension_key = _dimension_key(chart)
    metric_key = _metric_key(chart)
    metric_column = _column_by_key(chart, metric_key)
    dimension_column = _column_by_key(chart, dimension_key)
    if not metric_key or not metric_column:
        return []

    numeric_rows = _numeric_rows(chart, metric_key)
    summary_items = [
        {"label": "数据行数", "value": f"{len(chart.data.rows)} 条", "description": "当前图表使用的数据记录数。"}
    ]
    if numeric_rows:
        total = sum(value for _, value in numeric_rows)
        top_row, top_value = max(numeric_rows, key=lambda item: item[1])
        top_label = _row_label(top_row, dimension_key)
        summary_items.extend(
            [
                {
                    "label": f"合计{metric_column.label}",
                    "value": _format_value(total, metric_column),
                    "description": "按当前图表数据直接汇总。",
                },
                {
                    "label": f"最高{metric_column.label}",
                    "value": _format_value(top_value, metric_column),
                    "description": f"{top_label} 当前最高。",
                },
            ]
        )

    return [
        ChartAgentUiBlock(type=UI_BLOCK_METRIC_SUMMARY, title="指标摘要", items=summary_items),
        ChartAgentUiBlock(
            type=UI_BLOCK_INSIGHT_CARD,
            title="主要洞察",
            content=_insight_text(chart, dimension_column, metric_column, numeric_rows),
        ),
        ChartAgentUiBlock(type=UI_BLOCK_DATA_TABLE, title="数据明细", data=_data_table(chart)),
        ChartAgentUiBlock(type=UI_BLOCK_SUGGESTED_ACTIONS, title="建议操作", actions=_suggested_actions(chart)),
    ]


def _insight_text(
    chart: ChartSpec,
    dimension_column: ChartColumn | None,
    metric_column: ChartColumn,
    numeric_rows: list[tuple[dict[str, Any], float]],
) -> str:
    dimension_label = dimension_column.label if dimension_column else "当前维度"
    if not numeric_rows:
        return f"当前图表按{dimension_label}展示{metric_column.label}，共 {len(chart.data.rows)} 条数据。"

    top_row, top_value = max(numeric_rows, key=lambda item: item[1])
    bottom_row, bottom_value = min(numeric_rows, key=lambda item: item[1])
    dimension_key = _dimension_key(chart)
    return (
        f"当前图表按{dimension_label}展示{metric_column.label}，共 {len(chart.data.rows)} 条数据。"
        f"{_row_label(top_row, dimension_key)}最高，为{_format_value(top_value, metric_column)}；"
        f"{_row_label(bottom_row, dimension_key)}最低，为{_format_value(bottom_value, metric_column)}。"
    )


def _suggested_actions(chart: ChartSpec) -> list[dict[str, str]]:
    target_chart_type = CHART_TYPE_LINE if chart.chartType == CHART_TYPE_BAR else CHART_TYPE_BAR
    target_label = "折线图" if target_chart_type == CHART_TYPE_LINE else "柱状图"
    actions = [
        {"label": f"切换为{target_label}", "message": f"把当前图表切换为{target_label}"},
        {"label": "查看摘要", "message": "这个图表相关信息是什么？"},
    ]
    if _dimension_key(chart) == DIMENSION_CHANNEL:
        actions.append({"label": "查看渠道", "message": "有哪些渠道？"})
    if _has_dimension_value(chart, "天猫"):
        actions.append({"label": "隐藏天猫", "message": "不要显示天猫"})
    return actions


def _data_table(chart: ChartSpec) -> dict[str, Any]:
    return {
        "columns": chart.data.columns,
        "rows": chart.data.rows[:8],
    }


def _dimension_key(chart: ChartSpec) -> str | None:
    return chart.encoding.x or chart.encoding.category


def _metric_key(chart: ChartSpec) -> str | None:
    return chart.encoding.y or chart.encoding.value


def _column_by_key(chart: ChartSpec, key: str | None) -> ChartColumn | None:
    if not key:
        return None
    return next((column for column in chart.data.columns if column.key == key), None)


def _numeric_rows(chart: ChartSpec, metric_key: str) -> list[tuple[dict[str, Any], float]]:
    rows: list[tuple[dict[str, Any], float]] = []
    for row in chart.data.rows:
        value = row.get(metric_key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            rows.append((row, float(value)))
    return rows


def _row_label(row: dict[str, Any], dimension_key: str | None) -> str:
    if not dimension_key:
        return "当前分组"
    value = row.get(dimension_key)
    return str(value) if value is not None else "当前分组"


def _has_dimension_value(chart: ChartSpec, expected_value: str) -> bool:
    dimension_key = _dimension_key(chart)
    if not dimension_key:
        return False
    return any(row.get(dimension_key) == expected_value for row in chart.data.rows)


def _format_value(value: float, column: ChartColumn) -> str:
    if column.type == COLUMN_TYPE_CURRENCY:
        return f"{value:,.0f}"
    if column.type == COLUMN_TYPE_PERCENT:
        return f"{value * 100:.1f}%"
    if column.type == COLUMN_TYPE_NUMBER:
        return f"{value:,.0f}"
    return str(value)
