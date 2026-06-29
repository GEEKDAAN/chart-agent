from app.agents.chart_agent_graph import build_chart_agent_graph
from app.domain.ui_blocks import UI_BLOCK_DATA_TABLE, UI_BLOCK_INSIGHT_CARD, UI_BLOCK_METRIC_SUMMARY, UI_BLOCK_SUGGESTED_ACTIONS
from app.schemas.chart import ChartAgentAction
from app.services.ui_blocks import build_chart_ui_blocks

from tests.test_chart_agent_graph import _base_state


def test_create_chart_action_builds_controlled_ui_blocks():
    final_state = build_chart_agent_graph().invoke(_base_state("看最近30天各渠道销售额"))
    blocks = build_chart_ui_blocks(final_state["chart_action"])

    assert [block.type for block in blocks] == [
        UI_BLOCK_METRIC_SUMMARY,
        UI_BLOCK_INSIGHT_CARD,
        UI_BLOCK_DATA_TABLE,
        UI_BLOCK_SUGGESTED_ACTIONS,
    ]
    assert blocks[0].items[0].label == "数据行数"
    assert blocks[1].content is not None
    assert "最高" in blocks[1].content
    assert blocks[2].data is not None
    assert [column.key for column in blocks[2].data.columns] == ["channel", "sales"]
    assert len(blocks[2].data.rows) == 4
    assert blocks[3].actions[0].message.startswith("把当前图表切换为")


def test_non_create_chart_action_does_not_build_ui_blocks():
    action = ChartAgentAction(type="error", code="explanation", message="当前图表包含抖音。")

    assert build_chart_ui_blocks(action) == []
