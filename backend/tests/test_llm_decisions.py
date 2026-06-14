from app.agents.chart_agent_state import ChartAgentState
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


def test_low_confidence_llm_decision_falls_back(monkeypatch):
    monkeypatch.setattr(
        llm_decisions,
        "_generate_llm_decision",
        lambda state: ChartAgentDecision(
            intent="create_chart",
            toolName="create_chart",
            arguments={},
            confidence=0.2,
            reason="低置信度误判。",
            source="llm",
        ),
    )

    decision = llm_decisions.decide_chart_agent_tool(_base_state("有哪些渠道？", _chart()))

    assert decision.source == "fallback"
    assert decision.intent == "explain_chart"
    assert decision.toolName == "answer_current_chart_question"


def test_mismatched_llm_decision_falls_back(monkeypatch):
    monkeypatch.setattr(
        llm_decisions,
        "_generate_llm_decision",
        lambda state: ChartAgentDecision(
            intent="create_chart",
            toolName="answer_current_chart_question",
            arguments={},
            confidence=0.95,
            reason="工具和意图不匹配。",
            source="llm",
        ),
    )

    decision = llm_decisions.decide_chart_agent_tool(_base_state("抖音的销售额有多少？", _chart()))

    assert decision.source == "fallback"
    assert decision.intent == "explain_chart"
    assert decision.toolName == "answer_current_chart_question"


def test_llm_clarification_conflicting_with_chart_question_falls_back(monkeypatch):
    monkeypatch.setattr(
        llm_decisions,
        "_generate_llm_decision",
        lambda state: ChartAgentDecision(
            intent="unclear_chart_request",
            toolName="clarify_chart_request",
            arguments={},
            confidence=0.95,
            reason="误判为需求不明确。",
            source="llm",
        ),
    )

    decision = llm_decisions.decide_chart_agent_tool(_base_state("有哪些渠道？", _chart()))

    assert decision.source == "fallback"
    assert decision.intent == "explain_chart"
    assert decision.toolName == "answer_current_chart_question"


def test_valid_llm_decision_is_used(monkeypatch):
    monkeypatch.setattr(
        llm_decisions,
        "_generate_llm_decision",
        lambda state: ChartAgentDecision(
            intent="update_style",
            toolName="update_style",
            arguments={"target": "抖音", "color": "red"},
            confidence=0.93,
            reason="用户要求修改颜色。",
            source="llm",
        ),
    )

    decision = llm_decisions.decide_chart_agent_tool(_base_state("把抖音改成红色", _chart()))

    assert decision.source == "llm"
    assert decision.intent == "update_style"
    assert decision.toolName == "update_style"


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


def _chart() -> ChartSpec:
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
