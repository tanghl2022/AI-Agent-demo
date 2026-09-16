import time

from wms_agent.apps.warehouse.agent.events.event_context import (
    get_event_publisher
)

from wms_agent.apps.warehouse.agent.events.event_types import (
    AgentEventType
)


def create_query_location_node(
    wms_query_service
):

    async def query_location_node(
        state
    ):

        material_code = state.get(
            "material_code"
        )

        if not material_code:

            return {
                "status":
                    "CLARIFICATION_REQUIRED",

                "answer":
                    "请提供物料编码。"
            }

        publisher = (
            get_event_publisher()
        )

        # ====================================
        # Tool Start
        # ====================================

        if publisher:
            await publisher.publish(
                AgentEventType.TOOL_START,
                node="query_location",
                status="RUNNING",
                data={
                    "tool":
                        "query_location",
                    "materialCode":
                        material_code
                }
            )

        start_time = (
            time.perf_counter()
        )

        result = (await wms_query_service
            .query_locations(
                material_code
            )
        )

        duration_ms = int(
            (
                time.perf_counter()
                -
                start_time
            )
            * 1000
        )

        # ====================================
        # Tool End
        # ====================================

        if publisher:
            await publisher.publish(
                AgentEventType.TOOL_END,
                node="query_location",
                status="SUCCESS",
                data={
                    "tool":
                        "query_location",
                    "materialCode":
                        material_code,
                    "durationMs":
                        duration_ms
                }
            )
        if result.locations:

            location_text = "、".join(
                [
                    f"{item.location_code}（数量：{item.quantity}）"
                    for item in result.locations
                ]
            )

            answer = (
                f"物料 {result.material_code} 当前库位："
                f"{location_text}"
            )

        else:

            answer = (
                f"物料 {result.material_code} "
                f"当前未查询到库位信息。"
            )

        return {
            "status":
                "SUCCESS",

            "answer":
                answer,

            "active_workflow":
                None
        }

    return query_location_node