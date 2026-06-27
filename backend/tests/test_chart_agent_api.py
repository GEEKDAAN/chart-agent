from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_create_chart_returns_chart_action():
    response = client.post("/chart-agent/chat", json=_payload("看最近30天各渠道销售额"))

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "create_chart"
    assert body["action"]["type"] == "create_chart"
    assert body["action"]["chart"]["chartType"] == "bar"
    assert body["action"]["chart"]["encoding"]["x"] == "channel"
    assert body["action"]["chart"]["encoding"]["y"] == "sales"
    assert [block["type"] for block in body["uiBlocks"]] == ["metric_summary", "insight_card", "suggested_actions"]
    assert body["uiBlocks"][0]["items"][0]["label"] == "数据行数"
    assert "最高" in body["uiBlocks"][1]["content"]


def test_update_style_returns_patch_without_data_query():
    chart = _create_chart()

    response = client.post("/chart-agent/chat", json=_payload("把抖音改成红色", chart))

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "update_style"
    assert body["action"]["type"] == "update_chart"
    assert body["action"]["chartId"] == chart["id"]
    assert body["action"]["patch"]["style"]["colors"] == {"抖音": "#ef4444"}
    assert body["action"]["patch"]["data"] is None


def test_update_style_handles_multiple_targets_and_colors():
    chart = _create_chart()

    response = client.post("/chart-agent/chat", json=_payload("微信改成红色，天猫变成绿色", chart))

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "update_style"
    assert body["action"]["type"] == "update_chart"
    assert body["action"]["patch"]["style"]["colors"] == {"微信": "#ef4444", "天猫": "#16a34a"}


def test_update_style_yellow_is_not_treated_as_metric_question():
    chart = _create_chart()

    response = client.post("/chart-agent/chat", json=_payload("天猫变成黄色", chart))

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "update_style"
    assert body["action"]["type"] == "update_chart"
    assert body["action"]["patch"]["style"]["colors"] == {"天猫": "#facc15"}
    assert "186,000" not in body["action"]["message"]


def test_update_style_preserves_existing_colors_on_follow_up():
    chart = _create_chart()
    chart["style"]["colors"] = {"微信": "#ef4444"}

    response = client.post("/chart-agent/chat", json=_payload("天猫变成黄色", chart))

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "update_style"
    assert body["action"]["patch"]["style"]["colors"] == {"微信": "#ef4444", "天猫": "#facc15"}


def test_update_style_handles_excluded_target_for_remaining_categories():
    chart = _create_chart()

    response = client.post("/chart-agent/chat", json=_payload("除抖音外，其他改成绿色", chart))

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "update_style"
    assert body["action"]["type"] == "update_chart"
    assert body["action"]["patch"]["style"]["colors"] == {
        "小红书": "#16a34a",
        "微信": "#16a34a",
        "天猫": "#16a34a",
    }
    assert "抖音" not in body["action"]["patch"]["style"]["colors"]


def test_update_style_handles_all_categories():
    chart = _create_chart()

    response = client.post("/chart-agent/chat", json=_payload("全部变成蓝色", chart))

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "update_style"
    assert body["action"]["type"] == "update_chart"
    assert body["action"]["patch"]["style"]["colors"] == {
        "抖音": "#2563eb",
        "小红书": "#2563eb",
        "微信": "#2563eb",
        "天猫": "#2563eb",
    }


def test_hide_chart_category_updates_hidden_values():
    chart = _create_chart()

    response = client.post("/chart-agent/chat", json=_payload("不要显示天猫", chart))

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "update_style"
    assert body["action"]["type"] == "update_chart"
    assert body["action"]["patch"]["style"]["hiddenValues"] == {"channel": ["天猫"]}
    assert "186,000" not in body["action"]["message"]


def test_show_chart_category_removes_hidden_value():
    chart = _create_chart()
    chart["style"]["hiddenValues"] = {"channel": ["天猫"]}

    response = client.post("/chart-agent/chat", json=_payload("恢复显示天猫", chart))

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "update_style"
    assert body["action"]["patch"]["style"]["hiddenValues"] == {}


def test_update_data_adds_profit_rate_column():
    chart = _create_chart()

    response = client.post("/chart-agent/chat", json=_payload("加一列利润率", chart))

    assert response.status_code == 200
    body = response.json()
    columns = body["action"]["patch"]["data"]["columns"]
    assert body["intent"] == "update_data"
    assert body["action"]["type"] == "update_chart"
    assert [column["key"] for column in columns] == ["channel", "sales", "profit_rate"]


def test_change_chart_type_returns_type_patch():
    chart = _create_chart()

    response = client.post("/chart-agent/chat", json=_payload("换成折线图", chart))

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "change_chart_type"
    assert body["action"]["type"] == "update_chart"
    assert body["action"]["patch"]["chartType"] == "line"


def test_update_without_current_chart_returns_error():
    response = client.post("/chart-agent/chat", json=_payload("把抖音改成红色"))

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "update_style"
    assert body["action"]["type"] == "error"
    assert body["action"]["code"] == "validation_error"


def test_smalltalk_returns_conversational_response_without_chart_action():
    response = client.post("/chart-agent/chat", json=_payload("你好"))

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "smalltalk"
    assert body["action"]["type"] == "error"
    assert body["action"]["code"] == "smalltalk"
    assert "chart-agent" in body["action"]["message"]


def test_help_returns_capability_guidance():
    response = client.post("/chart-agent/chat", json=_payload("你能做什么"))

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "help"
    assert body["action"]["type"] == "error"
    assert body["action"]["code"] == "help"
    assert "生成图表" in body["action"]["message"]


def test_out_of_scope_returns_boundary_message():
    response = client.post("/chart-agent/chat", json=_payload("今天天气怎么样"))

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "out_of_scope"
    assert body["action"]["type"] == "error"
    assert body["action"]["code"] == "out_of_scope"


def test_unclear_request_asks_for_chart_details():
    response = client.post("/chart-agent/chat", json=_payload("帮我看看"))

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "unclear_chart_request"
    assert body["action"]["type"] == "error"
    assert body["action"]["code"] == "clarification_required"


def test_current_chart_question_returns_explanation():
    chart = _create_chart()

    response = client.post("/chart-agent/chat", json=_payload("这个图表相关信息是什么？", chart))

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "explain_chart"
    assert body["action"]["type"] == "error"
    assert body["action"]["code"] == "explanation"
    assert "当前图表" in body["action"]["message"]


def test_ambiguous_review_with_current_chart_returns_explanation():
    chart = _create_chart()

    response = client.post("/chart-agent/chat", json=_payload("帮我看看", chart))

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "explain_chart"
    assert body["action"]["code"] == "explanation"


def test_current_chart_dimension_question_lists_values():
    chart = _create_chart()

    response = client.post("/chart-agent/chat", json=_payload("有哪些渠道？", chart))

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "explain_chart"
    assert body["action"]["type"] == "error"
    assert body["action"]["code"] == "explanation"
    assert body["uiBlocks"] == []
    assert "抖音、小红书、微信、天猫" in body["action"]["message"]


def test_current_chart_metric_lookup_uses_existing_chart_data():
    chart = _create_chart()

    response = client.post("/chart-agent/chat", json=_payload("抖音的销售额有多少？", chart))

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "explain_chart"
    assert body["action"]["type"] == "error"
    assert body["action"]["code"] == "explanation"
    assert "抖音" in body["action"]["message"]
    assert "168,000" in body["action"]["message"]


def test_new_channel_chart_request_replaces_current_trend_chart():
    trend_chart = _create_chart("看近30天销售趋势")

    response = client.post("/chart-agent/chat", json=_payload("给我展示近30天各渠道的销售额", trend_chart))

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "create_chart"
    assert body["action"]["type"] == "create_chart"
    assert body["action"]["chart"]["encoding"]["x"] == "channel"
    assert body["action"]["chart"]["encoding"]["y"] == "sales"
    assert body["action"]["chart"]["chartType"] == "bar"


def _create_chart(message: str = "看最近30天各渠道销售额") -> dict:
    response = client.post("/chart-agent/chat", json=_payload(message))
    return response.json()["action"]["chart"]


def _payload(message: str, current_chart: dict | None = None) -> dict:
    return {
        "conversationId": "demo",
        "message": message,
        "currentChart": current_chart,
        "pageContext": {},
        "userContext": {"userId": "u_demo", "tenantId": "t_demo"},
    }
