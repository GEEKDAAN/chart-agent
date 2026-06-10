from app.agents.chart_agent_graph import build_chart_agent_graph
from app.agents.chart_agent_state import ChartAgentState
from app.schemas.chart import ChartAgentAction, UserContext


def test_update_style_does_not_query_metrics():
    calls = {"count": 0}

    def query_metrics_spy(metrics, dimensions, filters, time_range, limit):
        calls["count"] += 1
        raise AssertionError("style updates must not query metrics")

    chart = _create_chart(build_chart_agent_graph())
    graph = build_chart_agent_graph(query_metrics_fn=query_metrics_spy)
    state: ChartAgentState = {
        "conversation_id": "demo",
        "user_message": "把抖音改成红色",
        "current_chart": chart,
        "page_context": {},
        "user_context": UserContext(userId="u_demo", tenantId="t_demo"),
        "data_requirements": None,
        "queried_data": None,
        "chart_action": None,
        "assistant_message": "",
        "errors": [],
    }

    final_state = graph.invoke(state)

    assert calls["count"] == 0
    assert final_state["chart_action"].type == "update_chart"


def test_create_chart_queries_metrics_once():
    calls = {"count": 0}

    from app.services.metrics import query_metrics

    def query_metrics_spy(metrics, dimensions, filters, time_range, limit):
        calls["count"] += 1
        return query_metrics(metrics, dimensions, filters, time_range, limit)

    graph = build_chart_agent_graph(query_metrics_fn=query_metrics_spy)
    _create_chart(graph)

    assert calls["count"] == 1


def test_llm_action_is_used_when_valid():
    graph = build_chart_agent_graph(
        llm_action_fn=lambda state: ChartAgentAction(
            type="error",
            code="llm_generated",
            message="LLM 已接管生成动作。",
        )
    )
    state = _base_state("解释一下这个图", current_chart=None)

    final_state = graph.invoke(state)

    assert final_state["chart_action"].type == "error"
    assert final_state["chart_action"].code == "llm_generated"


def test_llm_failure_falls_back_to_deterministic_action():
    chart = _create_chart(build_chart_agent_graph())

    def failing_llm_action(state):
        raise RuntimeError("llm unavailable")

    graph = build_chart_agent_graph(llm_action_fn=failing_llm_action)
    final_state = graph.invoke(_base_state("把抖音改成红色", current_chart=chart))

    assert final_state["chart_action"].type == "update_chart"
    assert final_state["chart_action"].patch.style.colors == {"抖音": "#ef4444"}


def test_create_chart_parses_order_metric_and_channel_dimension():
    captured = {}

    from app.services.metrics import query_metrics

    def query_metrics_spy(metrics, dimensions, filters, time_range, limit):
        captured.update(
            {
                "metrics": metrics,
                "dimensions": dimensions,
                "filters": filters,
                "time_range": time_range,
                "limit": limit,
            }
        )
        return query_metrics(metrics, dimensions, filters, time_range, limit)

    graph = build_chart_agent_graph(query_metrics_fn=query_metrics_spy)
    final_state = graph.invoke(_base_state("看各渠道订单数"))

    assert final_state["intent"] == "create_chart"
    assert captured["metrics"] == ["orders"]
    assert captured["dimensions"] == ["channel"]
    assert captured["filters"] == {}
    assert final_state["chart_action"].type == "create_chart"


def test_create_chart_parses_recent_trend_time_range():
    captured = {}

    from app.services.metrics import query_metrics

    def query_metrics_spy(metrics, dimensions, filters, time_range, limit):
        captured.update(
            {
                "metrics": metrics,
                "dimensions": dimensions,
                "filters": filters,
                "time_range": time_range,
                "limit": limit,
            }
        )
        return query_metrics(metrics, dimensions, filters, time_range, limit)

    graph = build_chart_agent_graph(query_metrics_fn=query_metrics_spy)
    final_state = graph.invoke(_base_state("看最近7天销售额趋势"))

    assert captured["metrics"] == ["sales"]
    assert captured["dimensions"] == ["date"]
    assert captured["time_range"] is not None
    assert len(final_state["chart_action"].chart.data.rows) == 7
    assert final_state["chart_action"].chart.chartType == "line"


def _create_chart(graph):
    final_state = graph.invoke(_base_state("看最近30天各渠道销售额"))
    return final_state["chart_action"].chart


def _base_state(message: str, current_chart=None) -> ChartAgentState:
    return {
        "conversation_id": "demo",
        "user_message": message,
        "current_chart": current_chart,
        "page_context": {},
        "user_context": UserContext(userId="u_demo", tenantId="t_demo"),
        "data_requirements": None,
        "queried_data": None,
        "chart_action": None,
        "assistant_message": "",
        "errors": [],
    }
