import uuid

from wms_agent.events.event_context import get_event_publisher
from wms_agent.events.event_types import AgentEventType
from wms_agent.models.agent_state import (
    AgentState,
)


def create_freeze_workflow_adapter(
    freeze_workflow,
):

    async def freeze_workflow_adapter(
        state: AgentState,
    ) -> dict:

        material_code = state.get(
            "material_code"
        )

        quantity = state.get(
            "quantity"
        )

        if not material_code:

            return {
                "status":
                    "CLARIFICATION_REQUIRED",

                "answer":
                    "请提供物料编码。",
            }

        if quantity is None:

            return {
                "status":
                    "CLARIFICATION_REQUIRED",

                "answer":
                    f"你希望冻结"
                    f"{material_code}多少数量？",
            }

        # ====================================================
        # 每一个业务Workflow拥有独立实例ID
        # ====================================================

        workflow_instance_id = (
            state.get(
                "workflow_instance_id"
            )
        )

        if not workflow_instance_id:

            workflow_instance_id = (
                "freeze-"
                + str(uuid.uuid4())
            )

        freeze_input = {
            # 如果你现有FreezeState仍叫thread_id，
            # 这里保留即可。
            "thread_id":
                workflow_instance_id,

            "material_code":
                material_code,

            "quantity":
                quantity,
        }

        config = {
            "configurable": {
                "thread_id":
                    workflow_instance_id,
            }
        }
        publisher = get_event_publisher()

        if publisher:
            await publisher.publish(
                AgentEventType.WORKFLOW_START,
                node="freeze_inventory",
                status="RUNNING",
                workflow_instance_id=
                workflow_instance_id,
                data={
                    "workflow":
                        "FREEZE_INVENTORY",

                    "materialCode":
                        material_code,

                    "quantity":
                        quantity
                }
            )

        result = (
            await freeze_workflow.ainvoke(
                freeze_input,
                config=config,
            )
        )

        workflow_status = (
            result.get("status")
            or "WAITING_APPROVAL"
        )
        if (
                publisher
                and workflow_status
                == "WAITING_APPROVAL"
        ):
            await publisher.publish(
                AgentEventType.APPROVAL_REQUIRED,
                node="freeze_inventory",
                status="WAITING",
                workflow_instance_id=
                workflow_instance_id,
                data={
                    "message":
                        "库存冻结申请等待人工审批",

                    "materialCode":
                        material_code,

                    "quantity":
                        quantity
                }
            )
        return {
            "status":
                workflow_status,

            "active_workflow":
                "FREEZE_INVENTORY",

            "workflow_instance_id":
                workflow_instance_id,

            "answer":
                (
                    f"库存冻结申请已创建："
                    f"物料{material_code}，"
                    f"数量{quantity}，"
                    f"等待人工审批。"
                ),
        }

    return freeze_workflow_adapter
