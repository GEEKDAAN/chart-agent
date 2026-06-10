import pytest

from app.schemas.chart import UserContext
from app.services.metrics import (
    MetricService,
    MockMetricDataSource,
    get_metric_catalog,
    query_metrics,
    validate_data_access,
)


def test_metric_catalog_returns_supported_fields():
    catalog = get_metric_catalog(_user_context())

    assert [item["key"] for item in catalog["metrics"]] == ["sales", "orders", "profit_rate"]
    assert [item["key"] for item in catalog["dimensions"]] == ["date", "region", "channel"]


def test_validate_data_access_rejects_unknown_metric():
    with pytest.raises(ValueError, match="不支持"):
        validate_data_access(_user_context(), ["refund_amount"], ["channel"])


def test_validate_data_access_rejects_missing_user_context():
    with pytest.raises(ValueError, match="用户上下文不完整"):
        validate_data_access(UserContext(userId="", tenantId="t_demo"), ["sales"], ["channel"])


def test_query_metrics_filters_and_limits_rows():
    data = query_metrics(["sales", "orders"], ["channel"], {"channel": "抖音"}, None, 1)

    assert [column.key for column in data.columns] == ["channel", "sales", "orders"]
    assert data.rows == [{"channel": "抖音", "sales": 168000, "orders": 1240}]


def test_query_metrics_filters_channel_rows_by_region():
    data = query_metrics(["sales"], ["channel"], {"region": "华东"}, None, 10)

    assert [row["channel"] for row in data.rows] == ["抖音", "天猫"]


def test_query_metrics_rejects_unknown_dimension():
    with pytest.raises(ValueError, match="不支持"):
        query_metrics(["sales"], ["unknown_dimension"])


def test_query_metrics_uses_time_range_end_for_date_rows():
    data = query_metrics(["sales"], ["date"], {}, {"end": "2026-06-10"}, 10)

    assert data.rows[0]["date"] == "2026-06-04"
    assert data.rows[-1]["date"] == "2026-06-10"


def test_query_metrics_uses_time_range_start_and_end_for_date_rows():
    data = query_metrics(["sales"], ["date"], {}, {"start": "2026-06-01", "end": "2026-06-10"}, 20)

    assert len(data.rows) == 10
    assert data.rows[0]["date"] == "2026-06-01"
    assert data.rows[-1]["date"] == "2026-06-10"


def test_metric_service_accepts_replaceable_data_source():
    class StaticDataSource(MockMetricDataSource):
        def query(self, metrics, dimensions, filters, time_range, limit):
            data = super().query(metrics, dimensions, filters, time_range, limit)
            data.rows = data.rows[:1]
            return data

    service = MetricService(data_source=StaticDataSource())
    data = service.query(["sales"], ["region"], limit=500)

    assert len(data.rows) == 1
    assert data.rows[0]["region"] == "华东"


def _user_context() -> UserContext:
    return UserContext(userId="u_demo", tenantId="t_demo")
