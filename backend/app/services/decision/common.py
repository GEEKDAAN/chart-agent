from app.schemas.chart import ChartAgentDecision, Intent


def make_decision(intent: Intent, tool_name: str, source: str, reason: str) -> ChartAgentDecision:
    return ChartAgentDecision(
        intent=intent,
        toolName=tool_name,
        arguments={},
        confidence=1,
        reason=reason,
        source=source,
    )
