import json
from typing import Any

from app.agents.chart_agent_state import ChartAgentState
from app.core.config import get_settings
from app.schemas.chart import ChartAgentDecision, ChartSpec, Intent

MIN_LLM_CONFIDENCE = 0.6


def decide_chart_agent_tool(state: ChartAgentState) -> ChartAgentDecision:
    fallback_decision = fallback_chart_agent_decision(state)
    llm_decision = _generate_llm_decision(state)
    if llm_decision and _is_usable_decision(llm_decision, state, fallback_decision):
        return llm_decision
    return fallback_decision


def fallback_chart_agent_decision(state: ChartAgentState) -> ChartAgentDecision:
    message = state["user_message"]
    current_chart = state.get("current_chart")
    normalized = message.strip().lower()

    if normalized in {"你好", "您好", "hello", "hi", "嗨", "哈喽"}:
        return _decision("smalltalk", "smalltalk", "fallback", "用户在进行普通问候。")
    if any(keyword in normalized for keyword in ["你是谁", "你能做什么", "怎么用", "帮助", "help"]):
        return _decision("help", "help", "fallback", "用户在询问能力或使用方式。")
    if any(keyword in normalized for keyword in ["天气", "新闻", "写代码", "讲笑话", "翻译"]):
        return _decision("out_of_scope", "out_of_scope", "fallback", "用户请求超出图表 Agent 范围。")

    if any(keyword in normalized for keyword in ["红色", "颜色", "蓝色", "绿色"]):
        return _decision("update_style", "update_style", "fallback", "用户在修改图表样式。")
    if any(keyword in normalized for keyword in ["加一列", "新增指标", "加上", "增加指标"]):
        return _decision("update_data", "update_data", "fallback", "用户在更新图表数据指标。")
    if any(keyword in normalized for keyword in ["折线", "柱状", "饼图", "表格", "换成"]):
        return _decision("change_chart_type", "change_chart_type", "fallback", "用户在切换图表类型。")

    if current_chart and _looks_like_current_chart_question(normalized, current_chart):
        return _decision(
            "explain_chart",
            "answer_current_chart_question",
            "fallback",
            "用户在追问当前图表内容。",
        )

    if normalized in {"看看", "帮我看看", "看一下", "帮我看一下"}:
        if current_chart:
            return _decision(
                "explain_chart",
                "answer_current_chart_question",
                "fallback",
                "用户在要求查看当前图表。",
            )
        return _decision("unclear_chart_request", "clarify_chart_request", "fallback", "缺少可解释的当前图表。")

    if any(keyword in normalized for keyword in ["解释", "说明", "分析一下"]):
        return _decision("explain_chart", "answer_current_chart_question", "fallback", "用户在请求解释图表。")
    if any(keyword in normalized for keyword in ["看", "生成", "统计", "销售额", "订单数", "利润率", "趋势"]):
        return _decision("create_chart", "create_chart", "fallback", "用户在创建图表。")
    return _decision("unclear_chart_request", "clarify_chart_request", "fallback", "无法确定图表需求。")


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


def _generate_llm_decision(state: ChartAgentState) -> ChartAgentDecision | None:
    settings = get_settings()
    if settings.llm_mode != "openai" or not settings.openai_api_key:
        return None

    try:
        raw_decision = _call_openai_structured_decision(
            state,
            settings.openai_api_key,
            settings.openai_model,
            settings.openai_base_url,
        )
        decision = ChartAgentDecision.model_validate({**raw_decision, "source": "llm"})
        return decision
    except Exception:
        return None


def _call_openai_structured_decision(
    state: ChartAgentState,
    api_key: str,
    model: str,
    base_url: str | None,
) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)
    try:
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": _decision_system_prompt()},
                {"role": "user", "content": json.dumps(_build_decision_context(state), ensure_ascii=False)},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "chart_agent_decision",
                    "schema": _decision_schema(),
                    "strict": False,
                }
            },
        )
        return json.loads(response.output_text)
    except Exception:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _decision_system_prompt()},
                {"role": "user", "content": json.dumps(_build_decision_context(state), ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content or "{}")


def _is_usable_decision(
    decision: ChartAgentDecision,
    state: ChartAgentState,
    fallback_decision: ChartAgentDecision | None = None,
) -> bool:
    if decision.confidence < MIN_LLM_CONFIDENCE:
        return False
    if not _decision_intent_matches_tool(decision):
        return False
    if _conflicts_with_current_chart_question(decision, fallback_decision):
        return False
    if decision.toolName in {"update_style", "update_data", "change_chart_type", "answer_current_chart_question"}:
        return bool(state.get("current_chart")) or decision.toolName == "answer_current_chart_question"
    return True


def _conflicts_with_current_chart_question(
    decision: ChartAgentDecision,
    fallback_decision: ChartAgentDecision | None,
) -> bool:
    if not fallback_decision or fallback_decision.toolName != "answer_current_chart_question":
        return False
    return decision.toolName != "answer_current_chart_question"


def _decision_intent_matches_tool(decision: ChartAgentDecision) -> bool:
    mapping = {
        "create_chart": "create_chart",
        "update_style": "update_style",
        "update_data": "update_data",
        "change_chart_type": "change_chart_type",
        "answer_current_chart_question": "explain_chart",
        "clarify_chart_request": "unclear_chart_request",
        "smalltalk": "smalltalk",
        "help": "help",
        "out_of_scope": "out_of_scope",
    }
    return mapping[decision.toolName] == decision.intent


def _decision(intent: Intent, tool_name: str, source: str, reason: str) -> ChartAgentDecision:
    return ChartAgentDecision(
        intent=intent,
        toolName=tool_name,
        arguments={},
        confidence=1,
        reason=reason,
        source=source,
    )


def _decision_system_prompt() -> str:
    return (
        "你是 chart-agent 的工具决策节点。"
        "只能输出 JSON，不要输出解释文本。"
        "根据用户消息和 currentChart 选择一个后端工具。"
        "如果用户在询问当前图表字段、维度值、某个类别的指标值、最高最低或图表含义，选择 answer_current_chart_question。"
        "如果用户要创建新图表，选择 create_chart。"
        "如果用户要改颜色，选择 update_style。"
        "如果用户要增加指标或更新数据，选择 update_data。"
        "如果用户要换柱状图、折线图、饼图或表格，选择 change_chart_type。"
        "如果无法确定，选择 clarify_chart_request。"
    )


def _build_decision_context(state: ChartAgentState) -> dict[str, Any]:
    current_chart = state.get("current_chart")
    return {
        "message": state["user_message"],
        "currentChart": current_chart.model_dump(by_alias=True) if current_chart else None,
        "availableTools": [
            "create_chart",
            "update_style",
            "update_data",
            "change_chart_type",
            "answer_current_chart_question",
            "clarify_chart_request",
            "smalltalk",
            "help",
            "out_of_scope",
        ],
        "requiredOutput": {
            "intent": "one supported intent",
            "toolName": "one available tool",
            "arguments": {},
            "confidence": "0..1",
            "reason": "short Chinese reason",
        },
    }


def _decision_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "intent": {
                "type": "string",
                "enum": [
                    "create_chart",
                    "update_style",
                    "update_data",
                    "change_chart_type",
                    "explain_chart",
                    "smalltalk",
                    "help",
                    "out_of_scope",
                    "unclear_chart_request",
                    "unknown",
                ],
            },
            "toolName": {
                "type": "string",
                "enum": [
                    "create_chart",
                    "update_style",
                    "update_data",
                    "change_chart_type",
                    "answer_current_chart_question",
                    "clarify_chart_request",
                    "smalltalk",
                    "help",
                    "out_of_scope",
                ],
            },
            "arguments": {"type": "object"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "reason": {"type": "string"},
        },
        "required": ["intent", "toolName", "arguments", "confidence", "reason"],
    }


def _looks_like_current_chart_question(message: str, chart: ChartSpec) -> bool:
    if _contains_question_term(message):
        return True
    return _matches_chart_schema(message, chart) and not _looks_like_create_request(message)


def _contains_question_term(message: str) -> bool:
    return any(
        term in message
        for term in [
            "哪些",
            "多少",
            "是多少",
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


def _matches_chart_schema(message: str, chart: ChartSpec) -> bool:
    labels = [column.label.lower() for column in chart.data.columns]
    keys = [column.key.lower() for column in chart.data.columns]
    values = [str(value).lower() for row in chart.data.rows for value in row.values() if isinstance(value, str)]
    return any(token and token in message for token in [*labels, *keys, *values])


def _looks_like_create_request(message: str) -> bool:
    return any(keyword in message for keyword in ["生成", "创建", "新建", "重新生成", "统计", "趋势"])


def _asks_for_values(message: str) -> bool:
    return any(keyword in message for keyword in ["哪些", "有哪些", "有什么"])


def _asks_for_extreme(message: str) -> bool:
    return any(keyword in message for keyword in ["最高", "最大", "最低", "最小"])


def _resolve_dimension_key(message: str, chart: ChartSpec) -> str | None:
    candidates = [chart.encoding.x, chart.encoding.category]
    for column in chart.data.columns:
        if column.type == "string":
            candidates.append(column.key)
    return _resolve_column_key(message, chart, candidates)


def _resolve_metric_key(message: str, chart: ChartSpec) -> str | None:
    candidates = [chart.encoding.y, chart.encoding.value]
    for column in chart.data.columns:
        if column.type in {"number", "currency", "percent"}:
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
        if column_type == "percent":
            return f"{value:.0%}"
        if column_type == "currency":
            return f"{value:,.0f}"
        return f"{value:g}"
    return str(value)
