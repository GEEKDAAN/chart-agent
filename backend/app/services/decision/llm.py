import json
from typing import Any

from app.schemas.agent_state import ChartAgentState
from app.core.config import get_settings
from app.domain.decision_sources import DECISION_SOURCE_LLM
from app.domain.intents import (
    AVAILABLE_TOOLS,
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
)
from app.schemas.chart import ChartAgentDecision


def generate_llm_decision(state: ChartAgentState) -> ChartAgentDecision | None:
    settings = get_settings()
    if settings.llm_mode != "openai" or not settings.openai_api_key:
        return None

    try:
        raw_decision = _call_openai_structured_decision(
            state,
            settings.openai_api_key,
            settings.openai_model,
            settings.openai_base_url,
        )
        return ChartAgentDecision.model_validate({**raw_decision, "source": DECISION_SOURCE_LLM})
    except Exception:
        return None


def _call_openai_structured_decision(
    state: ChartAgentState,
    api_key: str,
    model: str,
    base_url: str | None,
) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)
    try:
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": _decision_system_prompt()},
                {"role": "user", "content": json.dumps(_build_decision_context(state), ensure_ascii=False)},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "chart_agent_decision",
                    "schema": _decision_schema(),
                    "strict": False,
                }
            },
        )
        return json.loads(response.output_text)
    except Exception:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _decision_system_prompt()},
                {"role": "user", "content": json.dumps(_build_decision_context(state), ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content or "{}")


def _decision_system_prompt() -> str:
    return (
        "你是 chart-agent 的工具决策节点。"
        "只能输出 JSON，不要输出解释文本。"
        "根据用户消息和 currentChart 选择一个后端工具。"
        "如果用户在询问当前图表字段、维度值、某个类别的指标值、最高最低或图表含义，选择 answer_current_chart_question。"
        "如果用户要创建新图表，或提出与 currentChart 不同的新维度、新指标、时间范围组合，选择 create_chart。"
        "如果用户要改颜色、隐藏或恢复显示图表类目，选择 update_style。"
        "如果用户要增加指标或更新数据，选择 update_data。"
        "如果用户要换柱状图、折线图、饼图或表格，选择 change_chart_type。"
        "如果无法确定，选择 clarify_chart_request。"
    )


def _build_decision_context(state: ChartAgentState) -> dict[str, Any]:
    current_chart = state.get("current_chart")
    return {
        "message": state["user_message"],
        "currentChart": current_chart.model_dump(by_alias=True) if current_chart else None,
        "availableTools": AVAILABLE_TOOLS,
        "requiredOutput": {
            "intent": "one supported intent",
            "toolName": "one available tool",
            "arguments": {},
            "confidence": "0..1",
            "reason": "short Chinese reason",
        },
    }


def _decision_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "intent": {
                "type": "string",
                "enum": [
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
                ],
            },
            "toolName": {
                "type": "string",
                "enum": AVAILABLE_TOOLS,
            },
            "arguments": {"type": "object"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "reason": {"type": "string"},
        },
        "required": ["intent", "toolName", "arguments", "confidence", "reason"],
    }
