from app.agents.chart_agent_graph import build_chart_agent_graph
from app.schemas.agent_state import ChartAgentState
from app.schemas.chart import ChartAgentAction, ChartAgentDecision, UserContext


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


def test_llm_decision_is_used_when_valid():
    chart = _create_chart(build_chart_agent_graph())

    graph = build_chart_agent_graph(
        decision_fn=lambda state: ChartAgentDecision(
            intent="explain_chart",
            toolName="answer_current_chart_question",
            arguments={},
            confidence=0.92,
            reason="用户在询问当前图表。",
            source="llm",
        )
    )

    final_state = graph.invoke(_base_state("有哪些渠道？", current_chart=chart))

    assert final_state["decision"].source == "llm"
    assert final_state["intent"] == "explain_chart"
    assert "抖音、小红书、微信、天猫" in final_state["chart_action"].message


def test_invalid_llm_decision_falls_back_to_deterministic_route():
    chart = _create_chart(build_chart_agent_graph())

    def invalid_decision(state):
        raise ValueError("invalid tool")

    graph = build_chart_agent_graph(decision_fn=invalid_decision)
    final_state = graph.invoke(_base_state("抖音的销售额有多少？", current_chart=chart))

    assert final_state["decision"].source == "fallback"
    assert final_state["intent"] == "explain_chart"
    assert "168,000" in final_state["chart_action"].message


def test_low_confidence_decision_can_be_replaced_by_fallback():
    from app.services.llm_decisions import fallback_chart_agent_decision

    chart = _create_chart(build_chart_agent_graph())

    def low_confidence_decision(state):
        decision = ChartAgentDecision(
            intent="create_chart",
            toolName="create_chart",
            arguments={},
            confidence=0.2,
            reason="低置信度误判。",
            source="llm",
        )
        if decision.confidence < 0.6:
            return fallback_chart_agent_decision(state)
        return decision

    graph = build_chart_agent_graph(decision_fn=low_confidence_decision)
    final_state = graph.invoke(_base_state("有哪些渠道？", current_chart=chart))

    assert final_state["decision"].source == "fallback"
    assert final_state["intent"] == "explain_chart"
    assert "抖音、小红书、微信、天猫" in final_state["chart_action"].message


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


def test_update_style_uses_controlled_tool_instead_of_llm_action():
    chart = _create_chart(build_chart_agent_graph())

    def wrong_llm_action(state):
        return ChartAgentAction(
            type="update_chart",
            chartId=chart.id,
            patch={"style": {"colors": {"微信": "#16a34a"}}},
            message="LLM 错误地把微信改成绿色。",
        )

    graph = build_chart_agent_graph(llm_action_fn=wrong_llm_action)
    final_state = graph.invoke(_base_state("微信改成红色，天猫变成绿色", current_chart=chart))

    assert final_state["intent"] == "update_style"
    assert final_state["chart_action"].patch.style.colors == {"微信": "#ef4444", "天猫": "#16a34a"}


def test_update_style_exclusion_uses_remaining_categories():
    chart = _create_chart(build_chart_agent_graph())
    graph = build_chart_agent_graph()

    final_state = graph.invoke(_base_state("除抖音外，其他改成绿色", current_chart=chart))

    assert final_state["intent"] == "update_style"
    assert final_state["chart_action"].patch.style.colors == {
        "小红书": "#16a34a",
        "微信": "#16a34a",
        "天猫": "#16a34a",
    }


def test_update_style_all_categories_does_not_default_to_first_category():
    calls = {"query": 0}
    chart = _create_chart(build_chart_agent_graph())

    def query_metrics_spy(metrics, dimensions, filters, time_range, limit):
        calls["query"] += 1
        raise AssertionError("style updates must not query metrics")

    graph = build_chart_agent_graph(query_metrics_fn=query_metrics_spy)
    final_state = graph.invoke(_base_state("全部变成蓝色", current_chart=chart))

    assert calls["query"] == 0
    assert final_state["intent"] == "update_style"
    assert final_state["chart_action"].patch.style.colors == {
        "抖音": "#2563eb",
        "小红书": "#2563eb",
        "微信": "#2563eb",
        "天猫": "#2563eb",
    }


def test_hide_category_does_not_query_metrics():
    calls = {"query": 0, "llm": 0}
    chart = _create_chart(build_chart_agent_graph())

    def query_metrics_spy(metrics, dimensions, filters, time_range, limit):
        calls["query"] += 1
        raise AssertionError("visibility updates must not query metrics")

    def llm_action_spy(state):
        calls["llm"] += 1
        raise AssertionError("visibility updates must not call LLM action generation")

    graph = build_chart_agent_graph(query_metrics_fn=query_metrics_spy, llm_action_fn=llm_action_spy)
    final_state = graph.invoke(_base_state("不要显示天猫", current_chart=chart))

    assert calls == {"query": 0, "llm": 0}
    assert final_state["intent"] == "update_style"
    assert final_state["chart_action"].patch.style.hiddenValues == {"channel": ["天猫"]}


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


def test_smalltalk_does_not_call_llm_or_query_metrics():
    calls = {"query": 0, "llm": 0}

    def query_metrics_spy(metrics, dimensions, filters, time_range, limit):
        calls["query"] += 1
        raise AssertionError("smalltalk must not query metrics")

    def llm_action_spy(state):
        calls["llm"] += 1
        raise AssertionError("smalltalk must not call LLM action generation")

    graph = build_chart_agent_graph(query_metrics_fn=query_metrics_spy, llm_action_fn=llm_action_spy)
    final_state = graph.invoke(_base_state("你好"))

    assert calls == {"query": 0, "llm": 0}
    assert final_state["intent"] == "smalltalk"
    assert final_state["chart_action"].type == "error"
    assert final_state["chart_action"].code == "smalltalk"


def test_current_chart_question_is_classified_as_explanation():
    chart = _create_chart(build_chart_agent_graph())
    graph = build_chart_agent_graph(llm_action_fn=lambda state: None)

    final_state = graph.invoke(_base_state("这个图怎么样？", current_chart=chart))

    assert final_state["intent"] == "explain_chart"
    assert final_state["chart_action"].type == "error"
    assert final_state["chart_action"].code == "explanation"


def test_current_chart_question_does_not_call_llm_or_query_metrics():
    calls = {"query": 0, "llm": 0}
    chart = _create_chart(build_chart_agent_graph())

    def query_metrics_spy(metrics, dimensions, filters, time_range, limit):
        calls["query"] += 1
        raise AssertionError("chart questions must not query metrics")

    def llm_action_spy(state):
        calls["llm"] += 1
        raise AssertionError("chart questions with current chart must not call LLM action generation")

    graph = build_chart_agent_graph(query_metrics_fn=query_metrics_spy, llm_action_fn=llm_action_spy)
    final_state = graph.invoke(_base_state("这个图表相关信息是什么？", current_chart=chart))

    assert calls == {"query": 0, "llm": 0}
    assert final_state["intent"] == "explain_chart"
    assert final_state["chart_action"].code == "explanation"


def test_current_chart_dimension_question_does_not_create_chart():
    calls = {"query": 0, "llm": 0}
    chart = _create_chart(build_chart_agent_graph())

    def query_metrics_spy(metrics, dimensions, filters, time_range, limit):
        calls["query"] += 1
        raise AssertionError("chart dimension questions must read current chart data")

    def llm_action_spy(state):
        calls["llm"] += 1
        raise AssertionError("deterministic chart questions must not call LLM action generation")

    graph = build_chart_agent_graph(query_metrics_fn=query_metrics_spy, llm_action_fn=llm_action_spy)
    final_state = graph.invoke(_base_state("有哪些渠道？", current_chart=chart))

    assert calls == {"query": 0, "llm": 0}
    assert final_state["intent"] == "explain_chart"
    assert "抖音、小红书、微信、天猫" in final_state["chart_action"].message


def test_current_chart_metric_lookup_does_not_create_chart():
    calls = {"query": 0, "llm": 0}
    chart = _create_chart(build_chart_agent_graph())

    def query_metrics_spy(metrics, dimensions, filters, time_range, limit):
        calls["query"] += 1
        raise AssertionError("chart metric lookup must read current chart data")

    def llm_action_spy(state):
        calls["llm"] += 1
        raise AssertionError("deterministic chart questions must not call LLM action generation")

    graph = build_chart_agent_graph(query_metrics_fn=query_metrics_spy, llm_action_fn=llm_action_spy)
    final_state = graph.invoke(_base_state("抖音的销售额有多少？", current_chart=chart))

    assert calls == {"query": 0, "llm": 0}
    assert final_state["intent"] == "explain_chart"
    assert "168,000" in final_state["chart_action"].message


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
