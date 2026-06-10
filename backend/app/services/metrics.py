from datetime import date, timedelta
from typing import Any

from app.schemas.chart import ChartColumn, ChartData, UserContext


METRIC_CATALOG = {
    "metrics": [
        {"key": "sales", "label": "销售额", "type": "currency"},
        {"key": "orders", "label": "订单数", "type": "number"},
        {"key": "profit_rate", "label": "利润率", "type": "percent"},
    ],
    "dimensions": [
        {"key": "date", "label": "日期", "type": "date"},
        {"key": "region", "label": "地区", "type": "string"},
        {"key": "channel", "label": "渠道", "type": "string"},
    ],
}

CHANNEL_ROWS = [
    {"channel": "抖音", "sales": 168000, "orders": 1240, "profit_rate": 0.23},
    {"channel": "小红书", "sales": 132000, "orders": 980, "profit_rate": 0.26},
    {"channel": "微信", "sales": 98000, "orders": 760, "profit_rate": 0.19},
    {"channel": "天猫", "sales": 186000, "orders": 1410, "profit_rate": 0.21},
]

REGION_ROWS = [
    {"region": "华东", "sales": 221000, "orders": 1660, "profit_rate": 0.24},
    {"region": "华南", "sales": 177000, "orders": 1290, "profit_rate": 0.22},
    {"region": "华北", "sales": 149000, "orders": 1040, "profit_rate": 0.18},
]


def get_metric_catalog(_: UserContext) -> dict[str, list[dict[str, str]]]:
    return METRIC_CATALOG


def validate_data_access(user_context: UserContext, metrics: list[str], dimensions: list[str]) -> None:
    metric_keys = {item["key"] for item in METRIC_CATALOG["metrics"]}
    dimension_keys = {item["key"] for item in METRIC_CATALOG["dimensions"]}
    invalid_metrics = [metric for metric in metrics if metric not in metric_keys]
    invalid_dimensions = [dimension for dimension in dimensions if dimension not in dimension_keys]
    if invalid_metrics or invalid_dimensions:
        raise ValueError("请求包含不支持的指标或维度")
    if not user_context.user_id or not user_context.tenant_id:
        raise ValueError("用户上下文不完整")


def query_metrics(
    metrics: list[str],
    dimensions: list[str],
    filters: dict[str, Any] | None = None,
    time_range: dict[str, str] | None = None,
    limit: int = 500,
) -> ChartData:
    filters = filters or {}
    dimension = dimensions[0] if dimensions else "channel"

    if dimension == "date":
        rows = _build_daily_rows(metrics)
    elif dimension == "region":
        rows = [row for row in REGION_ROWS if _matches_filters(row, filters)]
    else:
        rows = [row for row in CHANNEL_ROWS if _matches_filters(row, filters)]

    selected_rows = [
        {key: row[key] for key in [dimension, *metrics] if key in row}
        for row in rows[:limit]
    ]
    return ChartData(columns=_build_columns(dimension, metrics), rows=selected_rows)


def _build_columns(dimension: str, metrics: list[str]) -> list[ChartColumn]:
    catalog_items = {item["key"]: item for group in METRIC_CATALOG.values() for item in group}
    keys = [dimension, *metrics]
    return [
        ChartColumn(key=key, label=catalog_items[key]["label"], type=catalog_items[key]["type"])
        for key in keys
    ]


def _build_daily_rows(metrics: list[str]) -> list[dict[str, Any]]:
    start = date.today() - timedelta(days=6)
    rows: list[dict[str, Any]] = []
    for index in range(7):
        current = start + timedelta(days=index)
        base_sales = 82000 + index * 9200
        row = {
            "date": current.isoformat(),
            "sales": base_sales,
            "orders": 560 + index * 48,
            "profit_rate": round(0.18 + index * 0.008, 3),
        }
        rows.append({key: value for key, value in row.items() if key == "date" or key in metrics})
    return rows


def _matches_filters(row: dict[str, Any], filters: dict[str, Any]) -> bool:
    for key, value in filters.items():
        if value and row.get(key) != value:
            return False
    return True
