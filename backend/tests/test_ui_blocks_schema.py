import pytest
from pydantic import ValidationError

from app.domain.ui_blocks import (
    UI_BLOCK_DATA_TABLE,
    UI_BLOCK_INSIGHT_CARD,
    UI_BLOCK_METRIC_SUMMARY,
    UI_BLOCK_SUGGESTED_ACTIONS,
)
from app.schemas.chart import ChartAgentUiBlock, ChartColumn, DataTableBlockData


def test_metric_summary_block_requires_items():
    block = ChartAgentUiBlock(
        type=UI_BLOCK_METRIC_SUMMARY,
        title="指标摘要",
        items=[{"label": "最高渠道", "value": "天猫", "description": "销售额最高"}],
    )

    assert block.type == UI_BLOCK_METRIC_SUMMARY
    assert block.items and block.items[0].label == "最高渠道"


def test_insight_card_requires_content():
    block = ChartAgentUiBlock(
        type=UI_BLOCK_INSIGHT_CARD,
        title="洞察",
        content="天猫销售额最高，微信销售额最低。",
    )

    assert block.content == "天猫销售额最高，微信销售额最低。"


def test_suggested_actions_requires_actions():
    block = ChartAgentUiBlock(
        type=UI_BLOCK_SUGGESTED_ACTIONS,
        title="建议操作",
        actions=[{"label": "隐藏天猫", "message": "不要显示天猫"}],
    )

    assert block.actions and block.actions[0].message == "不要显示天猫"


def test_data_table_requires_data():
    block = ChartAgentUiBlock(
        type=UI_BLOCK_DATA_TABLE,
        title="明细",
        data=DataTableBlockData(
            columns=[ChartColumn(key="channel", label="渠道", type="string")],
            rows=[{"channel": "天猫"}],
        ),
    )

    assert block.data and block.data.rows == [{"channel": "天猫"}]


def test_invalid_block_type_is_rejected():
    with pytest.raises(ValidationError):
        ChartAgentUiBlock(type="unknown", title="非法")


def test_missing_required_payload_is_rejected():
    with pytest.raises(ValidationError):
        ChartAgentUiBlock(type=UI_BLOCK_INSIGHT_CARD, title="洞察")
