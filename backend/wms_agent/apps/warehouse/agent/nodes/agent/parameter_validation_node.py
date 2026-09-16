from wms_agent.apps.warehouse.agent.models.agent_state import AgentState

from wms_agent.apps.warehouse.agent.events.event_context import (
    get_event_publisher
)

from wms_agent.apps.warehouse.agent.events.event_types import (
    AgentEventType
)


async def validate_agent_parameters(
    state: AgentState
) -> dict:
    """
    LangGraph参数校验Node。
    """

    result = _do_validate(
        state
    )

    publisher = get_event_publisher()

    if publisher:

        await publisher.publish(
            AgentEventType.PARAMETER_VALIDATION,
            node="validate_parameters",
            status=result.get(
                "status"
            ),
            data={
                "intent":
                    state.get(
                        "intent"
                    ),

                "missingParameters":
                    result.get(
                        "missing_parameters",
                        []
                    )
            }
        )

    return result


def _do_validate(
    state: AgentState
) -> dict:

    intent = state.get(
        "intent"
    )

    material_code = state.get(
        "material_code"
    )

    quantity = state.get(
        "quantity"
    )

    # ========================================
    # QUERY_STOCK
    # ========================================

    if intent == "QUERY_STOCK":

        if not material_code:

            return {
                "status":
                    "CLARIFICATION_REQUIRED",

                "answer":
                    "请告诉我需要查询库存的物料编码。",

                "pending_intent":
                    "QUERY_STOCK",

                "missing_parameters":
                    ["material_code"]
            }

        return _success()

    # ========================================
    # QUERY_LOCATION
    # ========================================

    if intent == "QUERY_LOCATION":

        if not material_code:

            return {
                "status":
                    "CLARIFICATION_REQUIRED",

                "answer":
                    "请告诉我需要查询库位的物料编码。",

                "pending_intent":
                    "QUERY_LOCATION",

                "missing_parameters":
                    ["material_code"]
            }

        return _success()

    # ========================================
    # FREEZE_INVENTORY
    # ========================================

    if intent == "FREEZE_INVENTORY":

        missing = []

        if not material_code:
            missing.append(
                "material_code"
            )

        if quantity is None:
            missing.append(
                "quantity"
            )

        if (
            quantity is not None
            and quantity <= 0
        ):

            return {
                "status":
                    "CLARIFICATION_REQUIRED",

                "answer":
                    "冻结数量必须大于0，请重新输入。",

                "quantity":
                    None,

                "pending_intent":
                    "FREEZE_INVENTORY",

                "missing_parameters":
                    ["quantity"]
            }

        if missing:

            if missing == [
                "quantity"
            ]:

                answer = (
                    f"你希望冻结 "
                    f"{material_code} "
                    f"多少数量？"
                )

            elif missing == [
                "material_code"
            ]:

                answer = (
                    "请告诉我需要冻结库存的物料编码。"
                )

            else:

                answer = (
                    "请告诉我需要冻结的物料编码和数量。"
                )

            return {
                "status":
                    "CLARIFICATION_REQUIRED",

                "answer":
                    answer,

                "pending_intent":
                    "FREEZE_INVENTORY",

                "missing_parameters":
                    missing
            }

        return _success()

    return {
        "status":
            "UNKNOWN",

        "answer":
            "当前请求无法识别。",

        "pending_intent":
            None,

        "missing_parameters":
            []
    }


def _success() -> dict:

    return {
        "status":
            "RUNNING",

        "answer":
            "",

        "pending_intent":
            None,

        "missing_parameters":
            []
    }