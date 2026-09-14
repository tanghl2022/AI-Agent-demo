from typing import Any

from wms_agent.events.event_context import get_event_publisher
from wms_agent.events.event_types import AgentEventType
from wms_agent.models.agent_intent import (
    IntentResult,
)

from wms_agent.models.agent_state import (
    AgentState,
)


INTENT_RECOGNITION_SYSTEM_PROMPT = """
你是WMS仓储管理系统的业务意图识别器。

当前支持：

QUERY_STOCK
查询物料库存。

QUERY_LOCATION
查询物料所在库位。

FREEZE_INVENTORY
冻结某个物料一定数量的库存。

UNKNOWN
无法识别。

重要规则：

1. 你只负责理解当前用户这一轮明确说了什么。

2. 不允许执行任何WMS操作。

3. 不允许猜测参数。

4. 用户没有明确提供的参数必须返回null。

5. 如果系统提供了pending_intent，
说明上一轮正在等待用户补充该业务的参数。

例如：

pending_intent = FREEZE_INVENTORY

用户：
30个

这时可以结合pending_intent判断：
intent = FREEZE_INVENTORY
quantity = 30

但是：

material_code仍然应该返回null，
因为用户这一轮没有重新说物料编码。

历史参数合并由确定性的Context Merge Node完成，
不是你的职责。

6. 如果用户明确纠正参数，例如：

“不是MAT001，是MAT002，冻结30个”

则：
material_code = MAT002
quantity = 30

7. confidence必须在0到1之间。
""".strip()


def create_intent_recognition_node(
    chat_model: Any,
):
    publisher = get_event_publisher()

    structured_model = (
        chat_model
        .with_structured_output(
            IntentResult,
            # 使用工具调用返回结构化结果，避免发送不受支持的 json_schema。
            method="function_calling",
        )
    )

    async def intent_recognition_node(
            state: AgentState,
    ) -> dict:

        publisher = get_event_publisher()

        # ========================================
        # 1. 意图识别开始
        # ========================================

        if publisher:
            await publisher.publish(
                AgentEventType.INTENT_START,
                node="intent_recognition",
                status="RUNNING",
                data={
                    "message":
                        state.get(
                            "user_message",
                            ""
                        )
                }
            )

        user_message = (
                state.get("user_message")
                or ""
        ).strip()

        pending_intent = state.get(
            "pending_intent"
        )

        missing_parameters = (
                state.get(
                    "missing_parameters"
                )
                or []
        )

        runtime_context = f"""
    当前待补全业务：
    {pending_intent or "NONE"}

    当前缺少参数：
    {missing_parameters}
    """.strip()

        result: IntentResult = (
            await structured_model.ainvoke(
                [
                    (
                        "system",
                        INTENT_RECOGNITION_SYSTEM_PROMPT
                    ),
                    (
                        "system",
                        runtime_context
                    ),
                    (
                        "human",
                        user_message
                    )
                ]
            )
        )

        # ========================================
        # 2. 意图识别完成
        # ========================================

        if publisher:
            await publisher.publish(
                AgentEventType.INTENT_RESULT,
                node="intent_recognition",
                status="SUCCESS",
                data={
                    "intent":
                        result.intent.value,

                    "confidence":
                        result.confidence,

                    "materialCode":
                        result.material_code,

                    "quantity":
                        result.quantity,

                    "locationCode":
                        result.location_code
                }
            )

        return {
            "turn_intent":
                result.intent.value,

            "turn_confidence":
                result.confidence,

            "turn_material_code":
                result.material_code,

            "turn_quantity":
                result.quantity,

            "turn_location_code":
                result.location_code
        }

    return intent_recognition_node
