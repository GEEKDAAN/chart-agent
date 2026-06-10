from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Protocol

from app.schemas.chart import ChartColumn, ChartData, ColumnType, UserContext


@dataclass(frozen=True)
class CatalogField:
    key: str
    label: str
    type: ColumnType

    def to_dict(self) -> dict[str, str]:
        return {"key": self.key, "label": self.label, "type": self.type}


@dataclass(frozen=True)
class MetricCatalog:
    metrics: tuple[CatalogField, ...]
    dimensions: tuple[CatalogField, ...]

    def to_dict(self) -> dict[str, list[dict[str, str]]]:
        return {
            "metrics": [item.to_dict() for item in self.metrics],
            "dimensions": [item.to_dict() for item in self.dimensions],
        }

    def fields_by_key(self) -> dict[str, CatalogField]:
        return {item.key: item for item in [*self.metrics, *self.dimensions]}

    def metric_keys(self) -> set[str]:
        return {item.key for item in self.metrics}

    def dimension_keys(self) -> set[str]:
        return {item.key for item in self.dimensions}


class MetricDataSource(Protocol):
    def query(
        self,
        metrics: Sequence[str],
        dimensions: Sequence[str],
        filters: dict[str, Any],
        time_range: dict[str, str] | None,
        limit: int,
    ) -> ChartData:
        ...


DEFAULT_METRIC_CATALOG = MetricCatalog(
    metrics=(
        CatalogField(key="sales", label="销售额", type="currency"),
        CatalogField(key="orders", label="订单数", type="number"),
        CatalogField(key="profit_rate", label="利润率", type="percent"),
    ),
    dimensions=(
        CatalogField(key="date", label="日期", type="date"),
        CatalogField(key="region", label="地区", type="string"),
        CatalogField(key="channel", label="渠道", type="string"),
    ),
)


CHANNEL_ROWS = [
    {"channel": "抖音", "region": "华东", "sales": 168000, "orders": 1240, "profit_rate": 0.23},
    {"channel": "小红书", "region": "华南", "sales": 132000, "orders": 980, "profit_rate": 0.26},
    {"channel": "微信", "region": "华北", "sales": 98000, "orders": 760, "profit_rate": 0.19},
    {"channel": "天猫", "region": "华东", "sales": 186000, "orders": 1410, "profit_rate": 0.21},
]

REGION_ROWS = [
    {"region": "华东", "sales": 221000, "orders": 1660, "profit_rate": 0.24},
    {"region": "华南", "sales": 177000, "orders": 1290, "profit_rate": 0.22},
    {"region": "华北", "sales": 149000, "orders": 1040, "profit_rate": 0.18},
]


class MockMetricDataSource:
    def __init__(self, catalog: MetricCatalog = DEFAULT_METRIC_CATALOG):
        self.catalog = catalog

    def query(
        self,
        metrics: Sequence[str],
        dimensions: Sequence[str],
        filters: dict[str, Any],
        time_range: dict[str, str] | None,
        limit: int,
    ) -> ChartData:
        dimension = dimensions[0] if dimensions else "channel"
        rows = self._rows_for_dimension(dimension, metrics, filters, time_range)
        selected_rows = [
            {key: row[key] for key in [dimension, *metrics] if key in row}
            for row in rows[:limit]
        ]
        return ChartData(columns=self._build_columns(dimension, metrics), rows=selected_rows)

    def _rows_for_dimension(
        self,
        dimension: str,
        metrics: Sequence[str],
        filters: dict[str, Any],
        time_range: dict[str, str] | None,
    ) -> list[dict[str, Any]]:
        if dimension == "date":
            return [row for row in self._build_daily_rows(metrics, time_range) if _matches_filters(row, filters)]
        if dimension == "region":
            return [row for row in REGION_ROWS if _matches_filters(row, filters)]
        if dimension == "channel":
            return [row for row in CHANNEL_ROWS if _matches_filters(row, filters)]
        raise ValueError("请求包含不支持的维度")

    def _build_columns(self, dimension: str, metrics: Sequence[str]) -> list[ChartColumn]:
        catalog_items = self.catalog.fields_by_key()
        return [
            ChartColumn(key=key, label=catalog_items[key].label, type=catalog_items[key].type)
            for key in [dimension, *metrics]
        ]

    def _build_daily_rows(
        self,
        metrics: Sequence[str],
        time_range: dict[str, str] | None,
    ) -> list[dict[str, Any]]:
        start = _parse_iso_date(time_range.get("start")) if time_range else None
        end = _parse_iso_date(time_range.get("end")) if time_range else None
        current_end = end or date.today()
        current_start = start or current_end - timedelta(days=6)
        if current_start > current_end:
            current_start = current_end
        days = min((current_end - current_start).days + 1, 366)
        rows: list[dict[str, Any]] = []
        for index in range(days):
            current = current_start + timedelta(days=index)
            base_sales = 82000 + index * 9200
            row = {
                "date": current.isoformat(),
                "sales": base_sales,
                "orders": 560 + index * 48,
                "profit_rate": round(0.18 + index * 0.008, 3),
            }
            rows.append({key: value for key, value in row.items() if key == "date" or key in metrics})
        return rows


class MetricService:
    def __init__(
        self,
        catalog: MetricCatalog = DEFAULT_METRIC_CATALOG,
        data_source: MetricDataSource | None = None,
    ):
        self.catalog = catalog
        self.data_source = data_source or MockMetricDataSource(catalog)

    def get_catalog(self, user_context: UserContext) -> dict[str, list[dict[str, str]]]:
        self._validate_user_context(user_context)
        return self.catalog.to_dict()

    def validate_access(
        self,
        user_context: UserContext,
        metrics: Sequence[str],
        dimensions: Sequence[str],
    ) -> None:
        self._validate_user_context(user_context)
        invalid_metrics = [metric for metric in metrics if metric not in self.catalog.metric_keys()]
        invalid_dimensions = [
            dimension for dimension in dimensions if dimension not in self.catalog.dimension_keys()
        ]
        if invalid_metrics or invalid_dimensions:
            raise ValueError("请求包含不支持的指标或维度")

    def query(
        self,
        metrics: Sequence[str],
        dimensions: Sequence[str],
        filters: dict[str, Any] | None = None,
        time_range: dict[str, str] | None = None,
        limit: int = 500,
    ) -> ChartData:
        invalid_metrics = [metric for metric in metrics if metric not in self.catalog.metric_keys()]
        invalid_dimensions = [
            dimension for dimension in dimensions if dimension not in self.catalog.dimension_keys()
        ]
        if invalid_metrics or invalid_dimensions:
            raise ValueError("请求包含不支持的指标或维度")
        clean_limit = max(0, min(limit, 500))
        return self.data_source.query(metrics, dimensions, filters or {}, time_range, clean_limit)

    def _validate_user_context(self, user_context: UserContext) -> None:
        if not user_context.user_id or not user_context.tenant_id:
            raise ValueError("用户上下文不完整")


metric_service = MetricService()


def get_metric_catalog(user_context: UserContext) -> dict[str, list[dict[str, str]]]:
    return metric_service.get_catalog(user_context)


def validate_data_access(user_context: UserContext, metrics: list[str], dimensions: list[str]) -> None:
    metric_service.validate_access(user_context, metrics, dimensions)


def query_metrics(
    metrics: list[str],
    dimensions: list[str],
    filters: dict[str, Any] | None = None,
    time_range: dict[str, str] | None = None,
    limit: int = 500,
) -> ChartData:
    return metric_service.query(metrics, dimensions, filters, time_range, limit)


def _matches_filters(row: dict[str, Any], filters: dict[str, Any]) -> bool:
    for key, value in filters.items():
        if value and key in row and row.get(key) != value:
            return False
    return True


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
