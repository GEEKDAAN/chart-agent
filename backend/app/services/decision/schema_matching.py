from app.domain.dimensions import DECISION_DIMENSION_KEYWORDS
from app.domain.metrics import DECISION_METRIC_KEYWORDS
from app.schemas.chart import ChartSpec


def looks_like_current_chart_question(message: str, chart: ChartSpec) -> bool:
    if contains_question_term(message):
        return True
    return matches_chart_schema(message, chart) and not looks_like_create_request(message)


def looks_like_new_chart_request(message: str, chart: ChartSpec) -> bool:
    if contains_question_term(message):
        return False

    requested_dimension = requested_dimension_key(message)
    requested_metric = requested_metric_key(message)
    has_chart_request_verb = any(keyword in message for keyword in ["看", "展示", "显示", "生成", "创建", "新建", "统计"])
    has_time_range = "最近" in message or "近" in message
    current_dimension = chart.encoding.x or chart.encoding.category
    current_metric = chart.encoding.y or chart.encoding.value

    if requested_dimension and requested_dimension != current_dimension:
        return True
    if requested_dimension and requested_metric and has_chart_request_verb:
        return True
    if requested_metric and requested_metric != current_metric and has_chart_request_verb:
        return True
    return bool(requested_dimension and requested_metric and has_time_range)


def contains_question_term(message: str) -> bool:
    return any(
        term in message
        for term in [
            "哪些",
            "多少",
            "是多大",
            "有什么",
            "有哪些",
            "哪个",
            "最高",
            "最大",
            "最低",
            "最小",
            "信息",
            "怎么样",
            "如何",
            "说明什么",
            "代表什么",
            "什么意思",
            "含义",
            "结论",
            "洞察",
            "分析",
            "为什么",
            "对比",
            "差异",
            "情况",
        ]
    )


def matches_chart_schema(message: str, chart: ChartSpec) -> bool:
    labels = [column.label.lower() for column in chart.data.columns]
    keys = [column.key.lower() for column in chart.data.columns]
    values = [str(value).lower() for row in chart.data.rows for value in row.values() if isinstance(value, str)]
    return any(token and token in message for token in [*labels, *keys, *values])


def looks_like_create_request(message: str) -> bool:
    return any(keyword in message for keyword in ["生成", "创建", "新建", "重新生成", "统计", "趋势", "展示", "显示"])


def requested_dimension_key(message: str) -> str | None:
    for key, keywords in DECISION_DIMENSION_KEYWORDS.items():
        if any(keyword in message for keyword in keywords):
            return key
    return None


def requested_metric_key(message: str) -> str | None:
    for key, keywords in DECISION_METRIC_KEYWORDS.items():
        if any(keyword in message for keyword in keywords):
            return key
    return None
