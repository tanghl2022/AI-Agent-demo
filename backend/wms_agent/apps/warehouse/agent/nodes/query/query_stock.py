import time

from wms_agent.apps.warehouse.agent.capabilities.stock_query import StockQueryCapability
from wms_agent.apps.warehouse.agent.events.event_context import (
    get_event_publisher
)

from wms_agent.apps.warehouse.agent.events.event_types import (
    AgentEventType
)


def create_query_stock_node(
    capability: StockQueryCapability,
):

    async def query_stock_node(
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
                node="query_stock",
                status="RUNNING",
                data={
                    "tool":
                        "query_stock",

                    "materialCode":
                        material_code
                }
            )

        start_time = (
            time.perf_counter()
        )

        result = (
            await capability.execute(material_code)
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
                node="query_stock",
                status="SUCCESS",
                data={
                    "tool":
                        "query_stock",

                    "materialCode":
                        material_code,

                    "durationMs":
                        duration_ms,

                    "totalQty":
                        result.total_qty,

                    "reservedQty":
                        result.reserved_qty,

                    "frozenQty":
                        result.frozen_qty,

                    "availableQty":
                        result.available_qty
                }
            )

        answer = (
            f"物料 {result.material_code}："
            f"总库存 {result.total_qty}，"
            f"预占 {result.reserved_qty}，"
            f"冻结 {result.frozen_qty}，"
            f"可用库存 {result.available_qty}。"
        )

        return {
            "status":
                "SUCCESS",

            "answer":
                answer,

            "active_workflow":
                None
        }

    return query_stock_node