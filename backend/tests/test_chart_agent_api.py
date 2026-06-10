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


def _create_chart() -> dict:
    response = client.post("/chart-agent/chat", json=_payload("看最近30天各渠道销售额"))
    return response.json()["action"]["chart"]


def _payload(message: str, current_chart: dict | None = None) -> dict:
    return {
        "conversationId": "demo",
        "message": message,
        "currentChart": current_chart,
        "pageContext": {},
        "userContext": {"userId": "u_demo", "tenantId": "t_demo"},
    }
