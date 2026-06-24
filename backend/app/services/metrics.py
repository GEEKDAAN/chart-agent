from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Protocol

from app.domain.column_types import (
    COLUMN_TYPE_CURRENCY,
    COLUMN_TYPE_DATE,
    COLUMN_TYPE_NUMBER,
    COLUMN_TYPE_PERCENT,
    COLUMN_TYPE_STRING,
)
from app.domain.dimensions import DIMENSION_CHANNEL, DIMENSION_DATE, DIMENSION_REGION
from app.domain.metrics import METRIC_ORDERS, METRIC_PROFIT_RATE, METRIC_SALES
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
        CatalogField(key=METRIC_SALES, label="销售额", type=COLUMN_TYPE_CURRENCY),
        CatalogField(key=METRIC_ORDERS, label="订单数", type=COLUMN_TYPE_NUMBER),
        CatalogField(key=METRIC_PROFIT_RATE, label="利润率", type=COLUMN_TYPE_PERCENT),
    ),
    dimensions=(
        CatalogField(key=DIMENSION_DATE, label="日期", type=COLUMN_TYPE_DATE),
        CatalogField(key=DIMENSION_REGION, label="地区", type=COLUMN_TYPE_STRING),
        CatalogField(key=DIMENSION_CHANNEL, label="渠道", type=COLUMN_TYPE_STRING),
    ),
)


CHANNEL_ROWS = [
    {
        DIMENSION_CHANNEL: "抖音",
        DIMENSION_REGION: "华东",
        METRIC_SALES: 168000,
        METRIC_ORDERS: 1240,
        METRIC_PROFIT_RATE: 0.23,
    },
    {
        DIMENSION_CHANNEL: "小红书",
        DIMENSION_REGION: "华南",
        METRIC_SALES: 132000,
        METRIC_ORDERS: 980,
        METRIC_PROFIT_RATE: 0.26,
    },
    {
        DIMENSION_CHANNEL: "微信",
        DIMENSION_REGION: "华北",
        METRIC_SALES: 98000,
        METRIC_ORDERS: 760,
        METRIC_PROFIT_RATE: 0.19,
    },
    {
        DIMENSION_CHANNEL: "天猫",
        DIMENSION_REGION: "华东",
        METRIC_SALES: 186000,
        METRIC_ORDERS: 1410,
        METRIC_PROFIT_RATE: 0.21,
    },
]

REGION_ROWS = [
    {
        DIMENSION_REGION: "华东",
        METRIC_SALES: 221000,
        METRIC_ORDERS: 1660,
        METRIC_PROFIT_RATE: 0.24,
    },
    {
        DIMENSION_REGION: "华南",
        METRIC_SALES: 177000,
        METRIC_ORDERS: 1290,
        METRIC_PROFIT_RATE: 0.22,
    },
    {
        DIMENSION_REGION: "华北",
        METRIC_SALES: 149000,
        METRIC_ORDERS: 1040,
        METRIC_PROFIT_RATE: 0.18,
    },
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
        dimension = dimensions[0] if dimensions else DIMENSION_CHANNEL
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
        if dimension == DIMENSION_DATE:
            return [row for row in self._build_daily_rows(metrics, time_range) if _matches_filters(row, filters)]
        if dimension == DIMENSION_REGION:
            return [row for row in REGION_ROWS if _matches_filters(row, filters)]
        if dimension == DIMENSION_CHANNEL:
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
                DIMENSION_DATE: current.isoformat(),
                METRIC_SALES: base_sales,
                METRIC_ORDERS: 560 + index * 48,
                METRIC_PROFIT_RATE: round(0.18 + index * 0.008, 3),
            }
            rows.append({key: value for key, value in row.items() if key == DIMENSION_DATE or key in metrics})
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
