import uuid
from wms_agent.apps.warehouse.agent.events.event_context import get_event_publisher
from wms_agent.apps.warehouse.agent.events.event_types import AgentEventType
from wms_agent.apps.warehouse.workflows.freeze_inventory.service import FreezeWorkflowService


def create_freeze_workflow_adapter(service: FreezeWorkflowService):
    """适配 Agent 状态与流程应用服务，不再直接操作 LangGraph。"""
    async def freeze_workflow_adapter(state: dict) -> dict:
        material_code, quantity = state.get("material_code"), state.get("quantity")
        if not material_code:
            return {"status": "CLARIFICATION_REQUIRED", "answer": "请提供物料编码。"}
        if quantity is None or quantity <= 0:
            return {"status": "CLARIFICATION_REQUIRED", "answer": "请提供大于零的冻结数量。"}
        workflow_id = state.get("workflow_instance_id") or "freeze-" + str(uuid.uuid4())
        publisher = get_event_publisher()
        if publisher:
            await publisher.publish(AgentEventType.WORKFLOW_START, node="freeze_inventory", status="RUNNING",
                workflow_instance_id=workflow_id, data={"workflow": "FREEZE_INVENTORY",
                                                        "materialCode": material_code, "quantity": quantity})
        result = await service.start(thread_id=workflow_id, material_code=material_code, quantity=quantity)
        waiting = result["status"] == "WAITING_APPROVAL"
        if waiting and publisher:
            await publisher.publish(AgentEventType.APPROVAL_REQUIRED, node="freeze_inventory", status="WAITING",
                workflow_instance_id=workflow_id, data={"message": "库存冻结申请等待人工审批",
                                                        "materialCode": material_code, "quantity": quantity})
        return {"status": result["status"], "active_workflow": "FREEZE_INVENTORY" if waiting else None,
                "workflow_instance_id": workflow_id,
                "answer": f"库存冻结申请已创建：物料{material_code}，数量{quantity}，等待人工审批。"
                          if waiting else result.get("message", "冻结流程已结束")}
    return freeze_workflow_adapter
