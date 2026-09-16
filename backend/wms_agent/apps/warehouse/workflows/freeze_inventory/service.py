from typing import Any
from langgraph.types import Command


class FreezeWorkflowService:
    """封装图的调用协议，供 HTTP 和 Agent 两种入口复用。"""

    def __init__(self, graph: Any):
        self.graph = graph

    @staticmethod
    def _config(thread_id: str) -> dict:
        if not thread_id.strip():
            raise ValueError("流程实例编号不能为空")
        return {"configurable": {"thread_id": thread_id}}

    async def start(self, *, thread_id: str, material_code: str, quantity: int) -> dict:
        if not material_code.strip() or quantity <= 0:
            raise ValueError("物料编码不能为空且冻结数量必须大于零")
        config = self._config(thread_id)
        existing = await self.graph.aget_state(config)
        if existing.values:
            # 相同流程编号只允许相同申请，避免重发开始请求覆盖审批状态。
            if existing.values.get("material_code") != material_code or existing.values.get("quantity") != quantity:
                raise ValueError("流程编号已用于其他冻结申请")
            result = dict(existing.values)
            interrupts = [item for task in existing.tasks for item in task.interrupts]
            result["__interrupt__"] = interrupts
        else:
            result = await self.graph.ainvoke(
                {"thread_id": thread_id, "material_code": material_code, "quantity": quantity}, config=config,
            )
        return self._result(thread_id, result)

    async def resume(self, *, thread_id: str, approved: bool, approver_id: str, remark: str = "") -> dict:
        if not approver_id.strip():
            raise ValueError("审批人不能为空")
        config = self._config(thread_id)
        snapshot = await self.graph.aget_state(config)
        if not snapshot.values:
            raise ValueError("冻结流程不存在")
        if not snapshot.next:
            # 已完成流程返回原结果，不重复写入或执行。
            return self._result(thread_id, dict(snapshot.values))
        result = await self.graph.ainvoke(Command(resume={
            "thread_id": thread_id, "approved": approved,
            "approverId": approver_id.strip(), "remark": remark,
        }), config=config)
        return self._result(thread_id, result)

    @staticmethod
    def _result(thread_id: str, result: dict) -> dict:
        interrupts = [{"id": getattr(item, "id", None), "value": getattr(item, "value", None)}
                      for item in result.get("__interrupt__", ())]
        status = "WAITING_APPROVAL" if interrupts else result.get("status", "UNKNOWN")
        return {
            "success": status in {"WAITING_APPROVAL", "SUCCESS"},
            "status": status, "threadId": thread_id, "interrupts": interrupts,
            "message": result.get("message", ""), "approved": result.get("approved"),
            "materialCode": result.get("material_code"), "quantity": result.get("quantity"),
            "availableQty": result.get("available_qty"),
            "finalFrozenQty": result.get("final_frozen_qty"),
            "finalAvailableQty": result.get("final_available_qty"),
            "idempotencyKey": result.get("idempotency_key"), "executed": result.get("freeze_executed"),
        }
