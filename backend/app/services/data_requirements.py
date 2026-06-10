import re
from collections.abc import Iterable
from datetime import date, timedelta

from app.agents.chart_agent_state import DataRequirements
from app.schemas.chart import ChartSpec, Intent


METRIC_KEYWORDS = {
    "sales": ("销售额", "销售", "成交额", "GMV", "gmv"),
    "orders": ("订单数", "订单", "单量"),
    "profit_rate": ("利润率", "毛利率"),
}

DIMENSION_KEYWORDS = {
    "date": ("趋势", "每天", "每日", "日期", "按天", "折线"),
    "region": ("各地区", "按地区", "分地区", "地区分布"),
    "channel": ("各渠道", "按渠道", "分渠道", "渠道分布"),
}

REGION_VALUES = ("华东", "华南", "华北")
CHANNEL_VALUES = ("抖音", "小红书", "微信", "天猫")


def parse_data_requirements(
    message: str,
    intent: Intent,
    current_chart: ChartSpec | None = None,
    today: date | None = None,
) -> DataRequirements:
    if intent == "create_chart":
        metrics = _resolve_metrics(message, default=["sales"])
        dimensions = [_resolve_create_dimension(message)]
        return {
            "metrics": metrics,
            "dimensions": dimensions,
            "filters": _resolve_filters(message),
            "time_range": _resolve_time_range(message, today or date.today()),
        }

    if intent == "update_data":
        if not current_chart:
            raise ValueError("当前没有可修改的图表，请先创建一个图表。")
        metrics = _merge_metrics(_current_metrics(current_chart), _resolve_metrics(message, default=[]))
        if not metrics:
            metrics = ["sales"]
        dimension = current_chart.encoding.x or current_chart.encoding.category or _resolve_create_dimension(message)
        return {
            "metrics": metrics,
            "dimensions": [dimension],
            "filters": _resolve_filters(message),
            "time_range": _resolve_time_range(message, today or date.today()),
        }

    raise ValueError("当前意图不需要数据查询。")


def _resolve_metrics(message: str, default: list[str]) -> list[str]:
    metrics = [key for key, keywords in METRIC_KEYWORDS.items() if _contains_any(message, keywords)]
    return metrics or list(default)


def _resolve_create_dimension(message: str) -> str:
    for key in ("region", "channel", "date"):
        keywords = DIMENSION_KEYWORDS[key]
        if _contains_any(message, keywords):
            return key
    if _resolve_recent_days(message):
        return "date"
    if any(value in message for value in REGION_VALUES):
        return "channel"
    if any(value in message for value in CHANNEL_VALUES):
        return "date"
    return "channel"


def _resolve_filters(message: str) -> dict[str, str]:
    filters: dict[str, str] = {}
    region = _first_match(message, REGION_VALUES)
    channel = _first_match(message, CHANNEL_VALUES)
    if region and not _contains_any(message, DIMENSION_KEYWORDS["region"]):
        filters["region"] = region
    if channel and not _contains_any(message, DIMENSION_KEYWORDS["channel"]):
        filters["channel"] = channel
    return filters


def _resolve_time_range(message: str, today: date) -> dict[str, str] | None:
    days = _resolve_recent_days(message)
    if not days:
        return None
    end = today
    start = end - timedelta(days=days - 1)
    return {"start": start.isoformat(), "end": end.isoformat()}


def _resolve_recent_days(message: str) -> int | None:
    match = re.search(r"最近\s*(\d+)\s*天", message)
    if match:
        return max(1, min(int(match.group(1)), 366))
    if "近一周" in message or "最近一周" in message:
        return 7
    if "近一个月" in message or "最近一个月" in message:
        return 30
    return None


def _current_metrics(chart: ChartSpec) -> list[str]:
    candidates = [
        chart.encoding.y,
        chart.encoding.value,
        *(column.key for column in chart.data.columns),
    ]
    return [key for key in candidates if key in METRIC_KEYWORDS]


def _merge_metrics(existing: Iterable[str], requested: Iterable[str]) -> list[str]:
    metrics: list[str] = []
    for metric in [*existing, *requested]:
        if metric not in metrics:
            metrics.append(metric)
    return metrics


def _contains_any(message: str, keywords: Iterable[str]) -> bool:
    return any(keyword in message for keyword in keywords)


def _first_match(message: str, values: Iterable[str]) -> str | None:
    return next((value for value in values if value in message), None)
