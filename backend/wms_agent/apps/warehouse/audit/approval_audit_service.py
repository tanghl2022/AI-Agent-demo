from datetime import datetime

from wms_agent.apps.warehouse.audit.approval_audit import ApprovalAudit
from wms_agent.apps.warehouse.audit.approval_audit_repository import (
    ApprovalAuditRepository,
)


class ApprovalAuditService:
    """
    审批审计业务服务。
    """

    def __init__(
        self,
        repository: ApprovalAuditRepository,
    ):
        self.repository = repository

    # async def record_freeze_approval(
    #     self,
    #     *,
    #     thread_id: str,
    #     state: dict,
    # ) -> None:
    #     """
    #     保存库存冻结审批日志。
    #     """
    #
    #     audit = ApprovalAudit(
    #         thread_id=thread_id,
    #
    #         business_type=(
    #             "FREEZE_INVENTORY"
    #         ),
    #
    #         material_code=(
    #             state["material_code"]
    #         ),
    #
    #         quantity=int(
    #             state["quantity"]
    #         ),
    #
    #         approved=bool(
    #             state["approved"]
    #         ),
    #
    #         approver_id=(
    #             state["approver_id"]
    #         ),
    #
    #         remark=(
    #             state.get(
    #                 "approval_remark",
    #                 "",
    #             )
    #         ),
    #
    #         approval_time=(
    #             datetime.fromisoformat(
    #                 state[
    #                     "approval_time"
    #                 ]
    #             )
    #         ),
    #     )
    #
    #     await self.repository.save(
    #         audit
    #     )
    async def record_freeze_approval(
            self,
            *,
            thread_id: str,
            state: dict,
    ) -> bool:
        """
        保存库存冻结审批日志。

        True：
            本次真正新增。

        False：
            相同审批已经存在。
        """

        audit = ApprovalAudit(
            thread_id=thread_id,
            business_type="FREEZE_INVENTORY",

            material_code=state[
                "material_code"
            ],

            quantity=int(
                state["quantity"]
            ),

            approved=bool(
                state["approved"]
            ),

            approver_id=state[
                "approver_id"
            ],

            remark=state.get(
                "approval_remark",
                "",
            ),

            approval_time=datetime.fromisoformat(
                state["approval_time"]
            ),
        )

        return await self.repository.save(
            audit
        )