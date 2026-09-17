import pytest
from pydantic import ValidationError

from wms_agent.apps.warehouse.agent.state.agent_intent import (
    IntentResult,
    IntentType,
)


def test_should_create_freeze_inventory_intent():
    """
    正常场景：
    用户请求冻结 MAT001 30 个库存时，
    结构化结果应该能够保存意图和业务参数。
    """

    result = IntentResult(
        intent=IntentType.FREEZE_INVENTORY,
        confidence=0.98,
        material_code="MAT001",
        quantity=30,
        location_code=None,
    )

    assert result.intent == IntentType.FREEZE_INVENTORY
    assert result.confidence == 0.98
    assert result.material_code == "MAT001"
    assert result.quantity == 30
    assert result.location_code is None


def test_should_allow_missing_quantity_for_incomplete_request():
    """
    IntentResult只负责保存LLM识别结果。

    比如：
        帮我冻结 MAT001

    LLM可以识别这是库存冻结，
    但是 quantity 允许为空。

    后续由 Parameter Validation Node
    判断需要向用户补问。
    """

    result = IntentResult(
        intent=IntentType.FREEZE_INVENTORY,
        confidence=0.95,
        material_code="MAT001",
        quantity=None,
        location_code=None,
    )

    assert result.intent == IntentType.FREEZE_INVENTORY
    assert result.material_code == "MAT001"
    assert result.quantity is None


def test_confidence_should_not_be_greater_than_one():
    """
    confidence必须限制在0~1之间。
    """

    with pytest.raises(ValidationError):

        IntentResult(
            intent=IntentType.QUERY_STOCK,
            confidence=1.5,
            material_code="MAT001",
            quantity=None,
            location_code=None,
        )


def test_should_reject_unknown_intent_value():
    """
    不允许LLM随便创造一个新的intent。
    """

    with pytest.raises(ValidationError):

        IntentResult(
            intent="DELETE_INVENTORY",
            confidence=0.9,
            material_code="MAT001",
            quantity=None,
            location_code=None,
        )
