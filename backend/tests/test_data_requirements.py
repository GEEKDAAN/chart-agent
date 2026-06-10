from datetime import date

from app.schemas.chart import ChartColumn, ChartData, ChartEncoding, ChartSpec, ChartStyle
from app.services.data_requirements import parse_data_requirements


def test_parse_recent_sales_trend():
    requirements = parse_data_requirements(
        "看最近7天销售额趋势",
        "create_chart",
        today=date(2026, 6, 10),
    )

    assert requirements == {
        "metrics": ["sales"],
        "dimensions": ["date"],
        "filters": {},
        "time_range": {"start": "2026-06-04", "end": "2026-06-10"},
    }


def test_parse_region_filter_keeps_default_breakdown():
    requirements = parse_data_requirements(
        "看华东地区销售额",
        "create_chart",
        today=date(2026, 6, 10),
    )

    assert requirements["metrics"] == ["sales"]
    assert requirements["dimensions"] == ["channel"]
    assert requirements["filters"] == {"region": "华东"}


def test_parse_channel_orders_dimension():
    requirements = parse_data_requirements(
        "看各渠道订单数",
        "create_chart",
        today=date(2026, 6, 10),
    )

    assert requirements["metrics"] == ["orders"]
    assert requirements["dimensions"] == ["channel"]
    assert requirements["filters"] == {}


def test_parse_region_profit_rate_dimension():
    requirements = parse_data_requirements(
        "看各地区利润率",
        "create_chart",
        today=date(2026, 6, 10),
    )

    assert requirements["metrics"] == ["profit_rate"]
    assert requirements["dimensions"] == ["region"]
    assert requirements["filters"] == {}


def test_update_data_preserves_current_metrics_and_dimension():
    chart = ChartSpec(
        id="chart_demo",
        title="各渠道销售额",
        chartType="bar",
        data=ChartData(
            columns=[
                ChartColumn(key="channel", label="渠道", type="string"),
                ChartColumn(key="sales", label="销售额", type="currency"),
            ],
            rows=[{"channel": "抖音", "sales": 168000}],
        ),
        encoding=ChartEncoding(x="channel", y="sales"),
        style=ChartStyle(),
    )

    requirements = parse_data_requirements(
        "加上订单数",
        "update_data",
        current_chart=chart,
        today=date(2026, 6, 10),
    )

    assert requirements["metrics"] == ["sales", "orders"]
    assert requirements["dimensions"] == ["channel"]
