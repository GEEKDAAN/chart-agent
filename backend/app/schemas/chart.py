from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ChartType = Literal["bar", "line", "pie", "table"]
ColumnType = Literal["string", "number", "date", "currency", "percent"]
Intent = Literal[
    "create_chart",
    "update_style",
    "update_data",
    "change_chart_type",
    "explain_chart",
    "smalltalk",
    "help",
    "out_of_scope",
    "unclear_chart_request",
    "unknown",
]
ChartAgentToolName = Literal[
    "create_chart",
    "update_style",
    "update_data",
    "change_chart_type",
    "answer_current_chart_question",
    "clarify_chart_request",
    "smalltalk",
    "help",
    "out_of_scope",
]
DecisionSource = Literal["llm", "fallback"]


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

        if self.chartType in {"bar", "line"} and not (self.encoding.x and self.encoding.y):
            raise ValueError("bar and line charts require encoding.x and encoding.y")
        if self.chartType == "pie" and not (self.encoding.category and self.encoding.value):
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
    type: Literal["create_chart", "update_chart", "error"]
    message: str
    chart: ChartSpec | None = None
    chartId: str | None = None
    patch: ChartPatch | None = None
    code: str | None = None

    @model_validator(mode="after")
    def validate_action_payload(self) -> "ChartAgentAction":
        if self.type == "create_chart" and self.chart is None:
            raise ValueError("create_chart requires chart")
        if self.type == "update_chart" and (not self.chartId or self.patch is None):
            raise ValueError("update_chart requires chartId and patch")
        if self.type == "error" and not self.code:
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
