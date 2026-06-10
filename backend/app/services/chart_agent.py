from app.schemas.chart import (
    ChartAgentAction,
    ChartAgentRequest,
    ChartAgentResponse,
    ChartEncoding,
    ChartPatch,
    ChartSpec,
    ChartStyle,
    Intent,
)
from app.services.metrics import get_metric_catalog, query_metrics, validate_data_access


def run_chart_agent(request: ChartAgentRequest) -> ChartAgentResponse:
    intent = classify_intent(request.message)
    try:
        action = _route_intent(intent, request)
    except ValueError as error:
        action = ChartAgentAction(type="error", code="validation_error", message=str(error))
    return ChartAgentResponse(conversationId=request.conversation_id, intent=intent, action=action)


def classify_intent(message: str) -> Intent:
    normalized = message.strip().lower()
    if any(keyword in normalized for keyword in ["解释", "说明", "分析一下"]):
        return "explain_chart"
    if any(keyword in normalized for keyword in ["红色", "颜色", "蓝色", "绿色"]):
        return "update_style"
    if any(keyword in normalized for keyword in ["利润率", "订单数", "加一列", "新增指标"]):
        return "update_data"
    if any(keyword in normalized for keyword in ["折线", "柱状", "饼图", "表格", "换成"]):
        return "change_chart_type"
    if any(keyword in normalized for keyword in ["看", "生成", "统计", "销售额", "趋势"]):
        return "create_chart"
    return "unknown"


def _route_intent(intent: Intent, request: ChartAgentRequest) -> ChartAgentAction:
    if intent == "create_chart":
        return _create_chart(request)
    if intent == "update_style":
        return _update_style(request)
    if intent == "update_data":
        return _update_data(request)
    if intent == "change_chart_type":
        return _change_chart_type(request)
    if intent == "explain_chart":
        return _explain_chart(request)
    return ChartAgentAction(
        type="error",
        code="clarification_required",
        message="我还不能确定你想创建还是修改图表，请明确指标、维度或修改目标。",
    )


def _create_chart(request: ChartAgentRequest) -> ChartAgentAction:
    dimension = "date" if "趋势" in request.message or "折线" in request.message else "channel"
    chart_type = "line" if dimension == "date" else "bar"
    metrics = ["sales"]
    get_metric_catalog(request.user_context)
    validate_data_access(request.user_context, metrics, [dimension])
    data = query_metrics(metrics=metrics, dimensions=[dimension], filters={}, time_range=None)
    encoding = ChartEncoding(x=dimension, y="sales")
    chart = ChartSpec(
        id="chart_demo_sales",
        title="最近 30 天销售额",
        chartType=chart_type,
        data=data,
        encoding=encoding,
        style=ChartStyle(showLegend=False, showTooltip=True),
    )
    return ChartAgentAction(type="create_chart", chart=chart, message="已生成最近 30 天销售额图表。")


def _update_style(request: ChartAgentRequest) -> ChartAgentAction:
    current = _require_current_chart(request)
    color = "#ef4444"
    if "蓝色" in request.message:
        color = "#2563eb"
    if "绿色" in request.message:
        color = "#16a34a"

    colors = dict(current.style.colors or {})
    target = _resolve_style_target(request.message, current)
    colors[target] = color
    patch = ChartPatch(style=ChartStyle(colors=colors))
    return ChartAgentAction(
        type="update_chart",
        chartId=current.id,
        patch=patch,
        message=f"已将 {target} 调整为指定颜色。",
    )


def _update_data(request: ChartAgentRequest) -> ChartAgentAction:
    current = _require_current_chart(request)
    metrics = ["sales"]
    if "利润率" in request.message:
        metrics.append("profit_rate")
    if "订单数" in request.message:
        metrics.append("orders")

    dimension = current.encoding.x or current.encoding.category or "channel"
    validate_data_access(request.user_context, metrics, [dimension])
    data = query_metrics(metrics=metrics, dimensions=[dimension], filters={}, time_range=None)
    visible_columns = [column.key for column in data.columns]
    patch = ChartPatch(data=data, style=ChartStyle(visibleColumns=visible_columns))
    return ChartAgentAction(
        type="update_chart",
        chartId=current.id,
        patch=patch,
        message="已更新图表数据和指标列。",
    )


def _change_chart_type(request: ChartAgentRequest) -> ChartAgentAction:
    current = _require_current_chart(request)
    chart_type = _resolve_chart_type(request.message)
    if chart_type == "pie":
        category = current.encoding.x or current.encoding.category
        value = current.encoding.y or current.encoding.value
        patch = ChartPatch(chartType="pie", encoding=ChartEncoding(category=category, value=value))
    elif chart_type == "table":
        patch = ChartPatch(chartType="table")
    else:
        x = current.encoding.x or current.encoding.category
        y = current.encoding.y or current.encoding.value
        patch = ChartPatch(chartType=chart_type, encoding=ChartEncoding(x=x, y=y))
    return ChartAgentAction(
        type="update_chart",
        chartId=current.id,
        patch=patch,
        message=f"已切换为{_chart_type_label(chart_type)}。",
    )


def _explain_chart(request: ChartAgentRequest) -> ChartAgentAction:
    current = _require_current_chart(request)
    rows_count = len(current.data.rows)
    columns = "、".join(column.label for column in current.data.columns)
    return ChartAgentAction(
        type="error",
        code="explanation",
        message=f"当前图表「{current.title}」包含 {rows_count} 行数据，字段包括：{columns}。",
    )


def _require_current_chart(request: ChartAgentRequest) -> ChartSpec:
    if not request.current_chart:
        raise ValueError("当前没有可修改的图表，请先创建一个图表。")
    return request.current_chart


def _resolve_style_target(message: str, chart: ChartSpec) -> str:
    for row in chart.data.rows:
        for value in row.values():
            if isinstance(value, str) and value in message:
                return value
    first_dimension = chart.encoding.x or chart.encoding.category
    if first_dimension and chart.data.rows:
        value = chart.data.rows[0].get(first_dimension)
        if isinstance(value, str):
            return value
    return "default"


def _resolve_chart_type(message: str) -> str:
    if "折线" in message:
        return "line"
    if "饼图" in message:
        return "pie"
    if "表格" in message:
        return "table"
    return "bar"


def _chart_type_label(chart_type: str) -> str:
    return {"bar": "柱状图", "line": "折线图", "pie": "饼图", "table": "表格"}[chart_type]
