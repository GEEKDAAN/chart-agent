from app.schemas.agent_state import ChartAgentState
from app.domain.colors import STYLE_COLOR_TERMS
from app.domain.decision_sources import DECISION_SOURCE_FALLBACK
from app.domain.intents import (
    INTENT_CHANGE_CHART_TYPE,
    INTENT_CREATE_CHART,
    INTENT_EXPLAIN_CHART,
    INTENT_HELP,
    INTENT_OUT_OF_SCOPE,
    INTENT_SMALLTALK,
    INTENT_UNCLEAR_CHART_REQUEST,
    INTENT_UPDATE_DATA,
    INTENT_UPDATE_STYLE,
    TOOL_ANSWER_CURRENT_CHART_QUESTION,
    TOOL_CHANGE_CHART_TYPE,
    TOOL_CLARIFY_CHART_REQUEST,
    TOOL_CREATE_CHART,
    TOOL_HELP,
    TOOL_OUT_OF_SCOPE,
    TOOL_SMALLTALK,
    TOOL_UPDATE_DATA,
    TOOL_UPDATE_STYLE,
)
from app.schemas.chart import ChartAgentDecision
from app.services.decision.common import make_decision
from app.services.decision.schema_matching import (
    looks_like_current_chart_question,
    looks_like_new_chart_request,
)
from app.services.visibility_updates import looks_like_visibility_update


def fallback_chart_agent_decision(state: ChartAgentState) -> ChartAgentDecision:
    message = state["user_message"]
    current_chart = state.get("current_chart")
    normalized = message.strip().lower()

    if normalized in {"你好", "您好", "hello", "hi", "嗨", "哈喽"}:
        return make_decision(INTENT_SMALLTALK, TOOL_SMALLTALK, DECISION_SOURCE_FALLBACK, "用户在进行普通问候。")
    if any(keyword in normalized for keyword in ["你是谁", "你能做什么", "怎么用", "帮助", "help"]):
        return make_decision(INTENT_HELP, TOOL_HELP, DECISION_SOURCE_FALLBACK, "用户在询问能力或使用方式。")
    if any(keyword in normalized for keyword in ["天气", "新闻", "写代码", "讲笑话", "翻译"]):
        return make_decision(INTENT_OUT_OF_SCOPE, TOOL_OUT_OF_SCOPE, DECISION_SOURCE_FALLBACK, "用户请求超出图表 Agent 范围。")

    if _looks_like_style_update(normalized):
        return make_decision(INTENT_UPDATE_STYLE, TOOL_UPDATE_STYLE, DECISION_SOURCE_FALLBACK, "用户在修改图表样式。")
    if current_chart and looks_like_visibility_update(normalized, current_chart):
        return make_decision(INTENT_UPDATE_STYLE, TOOL_UPDATE_STYLE, DECISION_SOURCE_FALLBACK, "用户在修改图表显示范围。")
    if any(keyword in normalized for keyword in ["加一列", "新增指标", "加上", "增加指标"]):
        return make_decision(INTENT_UPDATE_DATA, TOOL_UPDATE_DATA, DECISION_SOURCE_FALLBACK, "用户在更新图表数据指标。")
    if any(keyword in normalized for keyword in ["折线", "柱状", "饼图", "表格", "换成"]):
        return make_decision(INTENT_CHANGE_CHART_TYPE, TOOL_CHANGE_CHART_TYPE, DECISION_SOURCE_FALLBACK, "用户在切换图表类型。")

    if current_chart and looks_like_new_chart_request(normalized, current_chart):
        return make_decision(INTENT_CREATE_CHART, TOOL_CREATE_CHART, DECISION_SOURCE_FALLBACK, "用户提出了新的图表维度或指标需求。")

    if current_chart and looks_like_current_chart_question(normalized, current_chart):
        return make_decision(
            INTENT_EXPLAIN_CHART,
            TOOL_ANSWER_CURRENT_CHART_QUESTION,
            DECISION_SOURCE_FALLBACK,
            "用户在追问当前图表内容。",
        )

    if normalized in {"看看", "帮我看看", "看一下", "帮我看一下"}:
        if current_chart:
            return make_decision(
                INTENT_EXPLAIN_CHART,
                TOOL_ANSWER_CURRENT_CHART_QUESTION,
                DECISION_SOURCE_FALLBACK,
                "用户在要求查看当前图表。",
            )
        return make_decision(INTENT_UNCLEAR_CHART_REQUEST, TOOL_CLARIFY_CHART_REQUEST, DECISION_SOURCE_FALLBACK, "缺少可解释的当前图表。")

    if any(keyword in normalized for keyword in ["解释", "说明", "分析一下"]):
        return make_decision(INTENT_EXPLAIN_CHART, TOOL_ANSWER_CURRENT_CHART_QUESTION, DECISION_SOURCE_FALLBACK, "用户在请求解释图表。")
    if any(keyword in normalized for keyword in ["看", "生成", "统计", "销售额", "订单数", "利润率", "趋势"]):
        return make_decision(INTENT_CREATE_CHART, TOOL_CREATE_CHART, DECISION_SOURCE_FALLBACK, "用户在创建图表。")
    return make_decision(INTENT_UNCLEAR_CHART_REQUEST, TOOL_CLARIFY_CHART_REQUEST, DECISION_SOURCE_FALLBACK, "无法确定图表需求。")


def _looks_like_style_update(message: str) -> bool:
    style_verbs = ["改成", "改为", "变成", "变为", "设为", "设置为", "调成", "调整为", "换成"]
    if "颜色" in message:
        return True
    return any(color in message for color in STYLE_COLOR_TERMS) and any(verb in message for verb in style_verbs)
