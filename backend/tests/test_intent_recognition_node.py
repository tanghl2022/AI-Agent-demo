from wms_agent.apps.warehouse.agent.models.agent_intent import (
    IntentResult,
    IntentType,
)
from wms_agent.apps.warehouse.agent.nodes.agent.intent_recognition_node import (
    create_intent_recognition_node,
)


class FakeStructuredModel:
    """
    模拟 with_structured_output() 返回的结构化模型。

    单元测试阶段不真正请求大模型，
    否则测试会受到：
    - 网络
    - API Key
    - Token费用
    - 模型稳定性

    等因素影响。
    """

    def __init__(self, result: IntentResult):
        self.result = result

    async def ainvoke(self, messages):
        """
        模拟模型异步调用。
        """

        return self.result


class FakeChatModel:
    """
    模拟 ChatModel。
    """

    def __init__(self, result: IntentResult):
        self.result = result
        self.output_schema = None

    def with_structured_output(self, schema, *, method):
        """
        模拟 LangChain：

        model.with_structured_output(IntentResult)
        """

        assert method == "function_calling"
        self.output_schema = schema

        return FakeStructuredModel(
            self.result
        )


async def test_should_recognize_freeze_inventory_intent():
    """
    测试：
    用户请求冻结库存时，
    Intent Node 能正确把结构化结果写入 AgentState。
    """

    fake_result = IntentResult(
        intent=IntentType.FREEZE_INVENTORY,
        confidence=0.98,
        material_code="MAT001",
        quantity=30,
        location_code=None,
    )

    fake_model = FakeChatModel(
        fake_result
    )

    node = create_intent_recognition_node(
        fake_model
    )

    state = {
        "thread_id": "agent-001",
        "user_message": "帮我冻结MAT001 30个",
    }

    result = await node(state)

    assert result["turn_intent"] == "FREEZE_INVENTORY"
    assert result["turn_confidence"] == 0.98
    assert result["turn_material_code"] == "MAT001"
    assert result["turn_quantity"] == 30
    assert result["turn_location_code"] is None


async def test_should_allow_missing_quantity():
    """
    用户说：
        帮我冻结 MAT001

    Intent Node 可以识别出冻结意图，
    quantity 允许为空。

    参数不足由后续 Parameter Validation Node 处理。
    """

    fake_result = IntentResult(
        intent=IntentType.FREEZE_INVENTORY,
        confidence=0.95,
        material_code="MAT001",
        quantity=None,
        location_code=None,
    )

    fake_model = FakeChatModel(
        fake_result
    )

    node = create_intent_recognition_node(
        fake_model
    )

    state = {
        "thread_id": "agent-002",
        "user_message": "帮我冻结MAT001",
    }

    result = await node(state)

    assert result["turn_intent"] == "FREEZE_INVENTORY"
    assert result["turn_material_code"] == "MAT001"
    assert result["turn_quantity"] is None


async def test_should_recognize_stock_query():
    """
    库存查询测试。
    """

    fake_result = IntentResult(
        intent=IntentType.QUERY_STOCK,
        confidence=0.99,
        material_code="MAT001",
        quantity=None,
        location_code=None,
    )

    fake_model = FakeChatModel(
        fake_result
    )

    node = create_intent_recognition_node(
        fake_model
    )

    state = {
        "thread_id": "agent-003",
        "user_message": "MAT001还有多少库存？",
    }

    result = await node(state)

    assert result["turn_intent"] == "QUERY_STOCK"
    assert result["turn_material_code"] == "MAT001"
