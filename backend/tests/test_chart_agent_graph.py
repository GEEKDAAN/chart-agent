from app.agents.chart_agent_graph import build_chart_agent_graph
from app.agents.chart_agent_state import ChartAgentState
from app.schemas.chart import UserContext


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


def _create_chart(graph):
    state: ChartAgentState = {
        "conversation_id": "demo",
        "user_message": "看最近30天各渠道销售额",
        "current_chart": None,
        "page_context": {},
        "user_context": UserContext(userId="u_demo", tenantId="t_demo"),
        "data_requirements": None,
        "queried_data": None,
        "chart_action": None,
        "assistant_message": "",
        "errors": [],
    }
    final_state = graph.invoke(state)
    return final_state["chart_action"].chart
