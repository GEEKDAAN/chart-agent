from app.schemas.chart import ChartAgentDecision, ChartAgentToolName, DecisionSource, Intent


def make_decision(
    intent: Intent,
    tool_name: ChartAgentToolName,
    source: DecisionSource,
    reason: str,
) -> ChartAgentDecision:
    return ChartAgentDecision(
        intent=intent,
        toolName=tool_name,
        arguments={},
        confidence=1,
        reason=reason,
        source=source,
    )
