from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.actions import ACTION_CREATE_CHART, ACTION_ERROR, ACTION_UPDATE_CHART
from app.domain.chart_types import CHART_TYPE_BAR, CHART_TYPE_LINE, CHART_TYPE_PIE, CHART_TYPE_TABLE, XY_CHART_TYPES
from app.domain.column_types import (
    COLUMN_TYPE_CURRENCY,
    COLUMN_TYPE_DATE,
    COLUMN_TYPE_NUMBER,
    COLUMN_TYPE_PERCENT,
    COLUMN_TYPE_STRING,
)
from app.domain.decision_sources import DECISION_SOURCE_FALLBACK, DECISION_SOURCE_LLM
from app.domain.intents import (
    INTENT_CHANGE_CHART_TYPE,
    INTENT_CREATE_CHART,
    INTENT_EXPLAIN_CHART,
    INTENT_HELP,
    INTENT_OUT_OF_SCOPE,
    INTENT_SMALLTALK,
    INTENT_UNCLEAR_CHART_REQUEST,
    INTENT_UNKNOWN,
    INTENT_UPDATE_DATA,
    INTENT_UPDATE_STYLE,
    TOOL_ANSWER_CURRENT_CHART_QUESTION,
    TOOL_CHANGE_CHART_TYPE,
    TOOL_CLARIFY_CHART_REQUEST,
    TOOL_CREATE_CHART,
    TOOL_HELP,
    TOOL_OUT_OF_SCOPE,
    TOOL_SMALLTALK,
    TOOL_UPDATE_DATA,
    TOOL_UPDATE_STYLE,
)

ChartType = Literal[
    CHART_TYPE_BAR,
    CHART_TYPE_LINE,
    CHART_TYPE_PIE,
    CHART_TYPE_TABLE,
]
ColumnType = Literal[
    COLUMN_TYPE_STRING,
    COLUMN_TYPE_NUMBER,
    COLUMN_TYPE_DATE,
    COLUMN_TYPE_CURRENCY,
    COLUMN_TYPE_PERCENT,
]
Intent = Literal[
    INTENT_CREATE_CHART,
    INTENT_UPDATE_STYLE,
    INTENT_UPDATE_DATA,
    INTENT_CHANGE_CHART_TYPE,
    INTENT_EXPLAIN_CHART,
    INTENT_SMALLTALK,
    INTENT_HELP,
    INTENT_OUT_OF_SCOPE,
    INTENT_UNCLEAR_CHART_REQUEST,
    INTENT_UNKNOWN,
]
ChartAgentToolName = Literal[
    TOOL_CREATE_CHART,
    TOOL_UPDATE_STYLE,
    TOOL_UPDATE_DATA,
    TOOL_CHANGE_CHART_TYPE,
    TOOL_ANSWER_CURRENT_CHART_QUESTION,
    TOOL_CLARIFY_CHART_REQUEST,
    TOOL_SMALLTALK,
    TOOL_HELP,
    TOOL_OUT_OF_SCOPE,
]
DecisionSource = Literal[DECISION_SOURCE_LLM, DECISION_SOURCE_FALLBACK]


class UserContext(BaseModel):
    user_id: str = Field(alias="userId")
    tenant_id: str = Field(alias="tenantId")


class ChartColumn(BaseModel):
    key: str
    label: str
    type: ColumnType


class ChartData(BaseModel):
    columns: list[ChartColumn]
    rows: list[dict[str, Any]]


class ChartEncoding(BaseModel):
    x: str | None = None
    y: str | None = None
    series: str | None = None
    category: str | None = None
    value: str | None = None


class ColumnStyle(BaseModel):
    color: str | None = None
    backgroundColor: str | None = None
    width: int | None = None


class ChartStyle(BaseModel):
    visibleColumns: list[str] | None = None
    colors: dict[str, str] | None = None
    hiddenValues: dict[str, list[str]] | None = None
    showLegend: bool = True
    showTooltip: bool = True
    stacked: bool = False
    smooth: bool = False
    columnStyles: dict[str, ColumnStyle] | None = None


class ChartSpec(BaseModel):
    id: str
    title: str
    chartType: ChartType
    data: ChartData
    encoding: ChartEncoding
    style: ChartStyle = Field(default_factory=ChartStyle)

    @model_validator(mode="after")
    def validate_encoding(self) -> "ChartSpec":
        column_keys = {column.key for column in self.data.columns}
        referenced = [
            self.encoding.x,
            self.encoding.y,
            self.encoding.series,
            self.encoding.category,
            self.encoding.value,
        ]
        missing = [key for key in referenced if key and key not in column_keys]
        if missing:
            raise ValueError(f"encoding references missing columns: {', '.join(missing)}")

        if self.style.visibleColumns:
            missing_visible = [key for key in self.style.visibleColumns if key not in column_keys]
            if missing_visible:
                raise ValueError(f"visibleColumns references missing columns: {', '.join(missing_visible)}")
        if self.style.hiddenValues:
            missing_hidden = [key for key in self.style.hiddenValues if key not in column_keys]
            if missing_hidden:
                raise ValueError(f"hiddenValues references missing columns: {', '.join(missing_hidden)}")

        if self.chartType in XY_CHART_TYPES and not (self.encoding.x and self.encoding.y):
            raise ValueError("bar and line charts require encoding.x and encoding.y")
        if self.chartType == CHART_TYPE_PIE and not (self.encoding.category and self.encoding.value):
            raise ValueError("pie charts require encoding.category and encoding.value")
        return self


class ChartPatch(BaseModel):
    title: str | None = None
    chartType: ChartType | None = None
    data: ChartData | None = None
    encoding: ChartEncoding | None = None
    style: ChartStyle | None = None

    model_config = {"extra": "forbid"}


class ChartAgentRequest(BaseModel):
    conversation_id: str = Field(alias="conversationId")
    message: str
    current_chart: ChartSpec | None = Field(default=None, alias="currentChart")
    page_context: dict[str, Any] = Field(default_factory=dict, alias="pageContext")
    user_context: UserContext = Field(alias="userContext")

    @field_validator("message")
    @classmethod
    def message_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be empty")
        return value


class ChartAgentAction(BaseModel):
    type: Literal[ACTION_CREATE_CHART, ACTION_UPDATE_CHART, ACTION_ERROR]
    message: str
    chart: ChartSpec | None = None
    chartId: str | None = None
    patch: ChartPatch | None = None
    code: str | None = None

    @model_validator(mode="after")
    def validate_action_payload(self) -> "ChartAgentAction":
        if self.type == ACTION_CREATE_CHART and self.chart is None:
            raise ValueError("create_chart requires chart")
        if self.type == ACTION_UPDATE_CHART and (not self.chartId or self.patch is None):
            raise ValueError("update_chart requires chartId and patch")
        if self.type == ACTION_ERROR and not self.code:
            raise ValueError("error requires code")
        return self


class ChartAgentDecision(BaseModel):
    intent: Intent
    toolName: ChartAgentToolName
    arguments: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0, le=1)
    reason: str = ""
    source: DecisionSource


class ChartAgentResponse(BaseModel):
    conversation_id: str = Field(alias="conversationId")
    intent: Intent
    action: ChartAgentAction
