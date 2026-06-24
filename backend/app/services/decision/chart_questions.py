from typing import Any

from app.domain.column_types import (
    COLUMN_TYPE_CURRENCY,
    COLUMN_TYPE_PERCENT,
    COLUMN_TYPE_STRING,
    NUMERIC_COLUMN_TYPES,
)
from app.schemas.chart import ChartSpec
from app.services.decision.schema_matching import contains_question_term


def answer_current_chart_question(message: str, chart: ChartSpec) -> str:
    normalized = message.strip().lower()
    dimension_key = _resolve_dimension_key(normalized, chart)
    metric_key = _resolve_metric_key(normalized, chart)
    row = _resolve_row(normalized, chart, dimension_key)

    if _asks_for_values(normalized) and dimension_key:
        values = _unique_values(chart, dimension_key)
        label = _column_label(chart, dimension_key)
        return f"当前图表包含这些{label}：{'、'.join(values)}。"

    if row and metric_key:
        dimension_label = _column_label(chart, dimension_key) if dimension_key else "项目"
        dimension_value = str(row.get(dimension_key, "该项")) if dimension_key else "该项"
        metric_label = _column_label(chart, metric_key)
        return f"{dimension_label}「{dimension_value}」的{metric_label}是 {_format_value(row.get(metric_key), chart, metric_key)}。"

    if metric_key and _asks_for_extreme(normalized):
        return _answer_extreme(normalized, chart, metric_key)

    rows_count = len(chart.data.rows)
    columns = "、".join(column.label for column in chart.data.columns)
    return f"当前图表「{chart.title}」包含 {rows_count} 行数据，字段包括：{columns}。"


def _asks_for_values(message: str) -> bool:
    return any(keyword in message for keyword in ["哪些", "有哪些", "有什么"])


def _asks_for_extreme(message: str) -> bool:
    return any(keyword in message for keyword in ["最高", "最大", "最低", "最小"])


def _resolve_dimension_key(message: str, chart: ChartSpec) -> str | None:
    candidates = [chart.encoding.x, chart.encoding.category]
    for column in chart.data.columns:
        if column.type == COLUMN_TYPE_STRING:
            candidates.append(column.key)
    return _resolve_column_key(message, chart, candidates)


def _resolve_metric_key(message: str, chart: ChartSpec) -> str | None:
    candidates = [chart.encoding.y, chart.encoding.value]
    for column in chart.data.columns:
        if column.type in NUMERIC_COLUMN_TYPES:
            candidates.append(column.key)
    return _resolve_column_key(message, chart, candidates)


def _resolve_column_key(message: str, chart: ChartSpec, candidates: list[str | None]) -> str | None:
    deduped = [candidate for index, candidate in enumerate(candidates) if candidate and candidate not in candidates[:index]]
    for key in deduped:
        label = _column_label(chart, key)
        if key.lower() in message or label.lower() in message:
            return key
    return deduped[0] if deduped else None


def _resolve_row(message: str, chart: ChartSpec, dimension_key: str | None) -> dict[str, Any] | None:
    if not dimension_key:
        return None
    for row in chart.data.rows:
        value = row.get(dimension_key)
        if isinstance(value, str) and value.lower() in message:
            return row
    return None


def _unique_values(chart: ChartSpec, key: str) -> list[str]:
    values: list[str] = []
    for row in chart.data.rows:
        value = row.get(key)
        if value is None:
            continue
        text = str(value)
        if text not in values:
            values.append(text)
    return values


def _answer_extreme(message: str, chart: ChartSpec, metric_key: str) -> str:
    rows = [row for row in chart.data.rows if isinstance(row.get(metric_key), int | float)]
    if not rows:
        return answer_current_chart_question("", chart)

    reverse = not any(keyword in message for keyword in ["最低", "最小"])
    target = sorted(rows, key=lambda row: row[metric_key], reverse=reverse)[0]
    dimension_key = _resolve_dimension_key(message, chart)
    dimension_label = _column_label(chart, dimension_key) if dimension_key else "项目"
    metric_label = _column_label(chart, metric_key)
    dimension_value = str(target.get(dimension_key, "该项")) if dimension_key else "该项"
    qualifier = "最高" if reverse else "最低"
    return f"{metric_label}{qualifier}的是{dimension_label}「{dimension_value}」，数值为 {_format_value(target.get(metric_key), chart, metric_key)}。"


def _column_label(chart: ChartSpec, key: str | None) -> str:
    if not key:
        return "字段"
    for column in chart.data.columns:
        if column.key == key:
            return column.label
    return key


def _column_type(chart: ChartSpec, key: str | None) -> str | None:
    if not key:
        return None
    for column in chart.data.columns:
        if column.key == key:
            return column.type
    return None


def _format_value(value: object, chart: ChartSpec, key: str) -> str:
    if value is None:
        return "空值"
    column_type = _column_type(chart, key)
    if isinstance(value, int | float):
        if column_type == COLUMN_TYPE_PERCENT:
            return f"{value:.0%}"
        if column_type == COLUMN_TYPE_CURRENCY:
            return f"{value:,.0f}"
        return f"{value:g}"
    return str(value)


__all__ = ["answer_current_chart_question", "contains_question_term"]
