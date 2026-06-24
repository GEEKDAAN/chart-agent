import json
from typing import Any

from app.agents.chart_agent_state import ChartAgentState
from app.core.config import get_settings
from app.domain.actions import ACTION_CREATE_CHART, ACTION_ERROR, ACTION_UPDATE_CHART, ALLOWED_ACTION_TYPES
from app.schemas.chart import ChartAgentAction


def generate_llm_action(state: ChartAgentState) -> ChartAgentAction | None:
    settings = get_settings()
    if settings.llm_mode != "openai" or not settings.openai_api_key:
        return None

    try:
        raw_action = _call_openai_structured_action(
            state,
            settings.openai_api_key,
            settings.openai_model,
            settings.openai_base_url,
        )
        return ChartAgentAction.model_validate(raw_action)
    except Exception:
        return None


def _call_openai_structured_action(
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
                {"role": "system", "content": _system_prompt()},
                {"role": "user", "content": json.dumps(_build_llm_context(state), ensure_ascii=False)},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "chart_agent_action",
                    "schema": _chart_agent_action_schema(),
                    "strict": False,
                }
            },
        )
        return json.loads(response.output_text)
    except Exception:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _system_prompt()},
                {"role": "user", "content": json.dumps(_build_llm_context(state), ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)


def _system_prompt() -> str:
    return (
        "你是 chart-agent 的图表动作生成节点。"
        "只能输出符合 ChartAgentAction 协议的 JSON 对象。"
        "不要生成 React、SQL 或 ECharts option。"
        "所有字段必须基于当前 ChartSpec、查询结果和用户消息。"
        "JSON 必须包含 type、message、chart、chartId、patch、code。"
        "不用的字段填 null。"
    )


def _build_llm_context(state: ChartAgentState) -> dict[str, Any]:
    current_chart = state.get("current_chart")
    queried_data = state.get("queried_data")
    return {
        "conversationId": state["conversation_id"],
        "intent": state.get("intent", "unknown"),
        "message": state["user_message"],
        "currentChart": current_chart.model_dump(by_alias=True) if current_chart else None,
        "dataRequirements": state.get("data_requirements"),
        "queriedData": queried_data.model_dump(by_alias=True) if queried_data else None,
        "allowedActionTypes": ALLOWED_ACTION_TYPES,
        "rules": [
            "create_chart 必须包含完整 chart。",
            "update_chart 必须包含 chartId 和受控 patch。",
            "error 必须包含 code 和 message。",
            "不要输出未知字段。",
            "不要修改 chart id。",
        ],
    }


def _chart_agent_action_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "type": {"type": "string", "enum": [ACTION_CREATE_CHART, ACTION_UPDATE_CHART, ACTION_ERROR]},
            "message": {"type": "string"},
            "chart": {"type": ["object", "null"]},
            "chartId": {"type": ["string", "null"]},
            "patch": {"type": ["object", "null"]},
            "code": {"type": ["string", "null"]},
        },
        "required": ["type", "message", "chart", "chartId", "patch", "code"],
    }
