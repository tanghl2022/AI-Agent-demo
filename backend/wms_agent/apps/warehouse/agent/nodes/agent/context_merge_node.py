from wms_agent.apps.warehouse.agent.models.agent_state import (
    AgentState,
)


def merge_agent_context(
    state: AgentState,
) -> dict:
    """
    合并历史业务上下文与当前轮LLM抽取结果。

    原则：

    当前用户明确提供的值
        >
    历史值

    当前用户没有提供
        ↓
    可以保留历史值

    但只能在同一个pending intent上下文中使用。
    """

    turn_intent = state.get(
        "turn_intent"
    )

    pending_intent = state.get(
        "pending_intent"
    )

    old_intent = state.get(
        "intent"
    )

    # ========================================================
    # 1. 确定业务Intent
    # ========================================================

    if (
        pending_intent
        and (
            turn_intent == pending_intent
            or turn_intent == "UNKNOWN"
        )
    ):
        intent = pending_intent

    elif turn_intent:

        intent = turn_intent

    else:

        intent = old_intent

    # ========================================================
    # 2. 判断是否允许继承历史参数
    # ========================================================

    same_business_context = (
        pending_intent is not None
        and intent == pending_intent
    )

    # ========================================================
    # 3. material_code
    # ========================================================

    turn_material_code = state.get(
        "turn_material_code"
    )

    if turn_material_code is not None:

        material_code = (
            turn_material_code
        )

    elif same_business_context:

        material_code = state.get(
            "material_code"
        )

    else:

        material_code = None

    # ========================================================
    # 4. quantity
    # ========================================================

    turn_quantity = state.get(
        "turn_quantity"
    )

    if turn_quantity is not None:

        quantity = turn_quantity

    elif same_business_context:

        quantity = state.get(
            "quantity"
        )

    else:

        quantity = None

    # ========================================================
    # 5. location_code
    # ========================================================

    turn_location_code = state.get(
        "turn_location_code"
    )

    if turn_location_code is not None:

        location_code = (
            turn_location_code
        )

    elif same_business_context:

        location_code = state.get(
            "location_code"
        )

    else:

        location_code = None

    return {
        "intent":
            intent,

        "confidence":
            state.get(
                "turn_confidence"
            ),

        "material_code":
            material_code,

        "quantity":
            quantity,

        "location_code":
            location_code,

        "previous_user_message":
            state.get(
                "user_message"
            ),
    }