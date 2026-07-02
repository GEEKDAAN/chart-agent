import pytest

from app.schemas.agent_state import ChartAgentState
from app.schemas.chart import (
    ChartAgentDecision,
    ChartColumn,
    ChartData,
    ChartEncoding,
    ChartSpec,
    ChartStyle,
    UserContext,
)
from app.services import llm_decisions


@pytest.mark.parametrize(
    ("message", "chart_name", "expected_intent", "expected_tool"),
    [
        ("看近30天销售趋势", None, "create_chart", "create_chart"),
        ("给我展示近30天各渠道的销售额", "trend", "create_chart", "create_chart"),
        ("看最近30天销售趋势", "channel", "create_chart", "create_chart"),
        ("有哪些渠道？", "channel", "explain_chart", "answer_current_chart_question"),
        ("抖音的销售额有多少？", "channel", "explain_chart", "answer_current_chart_question"),
        ("这个图说明什么？", "channel", "explain_chart", "answer_current_chart_question"),
        ("把抖音改成红色", "channel", "update_style", "update_style"),
        ("除抖音外全部改成绿色", "channel", "update_style", "update_style"),
        ("全部变成蓝色", "channel", "update_style", "update_style"),
        ("不要显示天猫", "channel", "update_style", "update_style"),
        ("恢复显示天猫", "hidden_channel", "update_style", "update_style"),
        ("换成折线图", "channel", "change_chart_type", "change_chart_type"),
        ("加一列利润率", "channel", "update_data", "update_data"),
        ("你好", None, "smalltalk", "smalltalk"),
        ("今天天气怎么样", None, "out_of_scope", "out_of_scope"),
    ],
)
def test_fallback_decision_matrix(message, chart_name, expected_intent, expected_tool):
    decision = llm_decisions.fallback_chart_agent_decision(_base_state(message, _chart_by_name(chart_name)))

    assert decision.intent == expected_intent
    assert decision.toolName == expected_tool


@pytest.mark.parametrize(
    ("message", "chart_name", "llm_intent", "llm_tool", "expected_source", "expected_tool"),
    [
        ("给我展示近30天各渠道的销售额", "trend", "explain_chart", "answer_current_chart_question", "fallback", "create_chart"),
        ("把抖音改成红色", "channel", "explain_chart", "answer_current_chart_question", "fallback", "update_style"),
        ("不要显示天猫", "channel", "explain_chart", "answer_current_chart_question", "fallback", "update_style"),
        ("换成折线图", "channel", "explain_chart", "answer_current_chart_question", "fallback", "change_chart_type"),
        ("有哪些渠道？", "channel", "create_chart", "create_chart", "fallback", "answer_current_chart_question"),
        ("把抖音改成红色", "channel", "update_style", "update_style", "llm", "update_style"),
    ],
)
def test_llm_conflict_matrix_uses_backend_guardrails(
    monkeypatch,
    message,
    chart_name,
    llm_intent,
    llm_tool,
    expected_source,
    expected_tool,
):
    monkeypatch.setattr(
        llm_decisions,
        "_generate_llm_decision",
        lambda state: ChartAgentDecision(
            intent=llm_intent,
            toolName=llm_tool,
            arguments={},
            confidence=0.95,
            reason="测试用 LLM 决策。",
            source="llm",
        ),
    )

    decision = llm_decisions.decide_chart_agent_tool(_base_state(message, _chart_by_name(chart_name)))

    assert decision.source == expected_source
    assert decision.toolName == expected_tool


def _base_state(message: str, chart: ChartSpec | None = None) -> ChartAgentState:
    return {
        "conversation_id": "demo",
        "user_message": message,
        "current_chart": chart,
        "page_context": {},
        "user_context": UserContext(userId="u_demo", tenantId="t_demo"),
        "data_requirements": None,
        "queried_data": None,
        "chart_action": None,
        "assistant_message": "",
        "errors": [],
    }


def _chart_by_name(name: str | None) -> ChartSpec | None:
    if name == "channel":
        return _channel_chart()
    if name == "hidden_channel":
        chart = _channel_chart()
        chart.style.hiddenValues = {"channel": ["天猫"]}
        return chart
    if name == "trend":
        return _trend_chart()
    return None


def _channel_chart() -> ChartSpec:
    return ChartSpec(
        id="chart_demo_sales",
        title="各渠道销售额",
        chartType="bar",
        data=ChartData(
            columns=[
                ChartColumn(key="channel", label="渠道", type="string"),
                ChartColumn(key="sales", label="销售额", type="currency"),
            ],
            rows=[
                {"channel": "抖音", "sales": 168000},
                {"channel": "小红书", "sales": 132000},
                {"channel": "微信", "sales": 98000},
                {"channel": "天猫", "sales": 186000},
            ],
        ),
        encoding=ChartEncoding(x="channel", y="sales"),
        style=ChartStyle(showLegend=False, showTooltip=True),
    )


def _trend_chart() -> ChartSpec:
    return ChartSpec(
        id="chart_demo_sales_trend",
        title="日期趋势销售额",
        chartType="line",
        data=ChartData(
            columns=[
                ChartColumn(key="date", label="日期", type="date"),
                ChartColumn(key="sales", label="销售额", type="currency"),
            ],
            rows=[
                {"date": "2026-06-18", "sales": 120000},
                {"date": "2026-06-19", "sales": 132000},
                {"date": "2026-06-20", "sales": 128000},
            ],
        ),
        encoding=ChartEncoding(x="date", y="sales"),
        style=ChartStyle(showLegend=False, showTooltip=True),
    )
