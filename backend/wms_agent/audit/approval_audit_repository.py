from psycopg import AsyncConnection

from wms_agent.audit.approval_audit import ApprovalAudit


class ApprovalAuditRepository:
    """
    审批审计 Repository。
    """

    def __init__(
        self,
        connection: AsyncConnection,
    ):
        self.connection = connection

    # async def save(
    #     self,
    #     audit: ApprovalAudit,
    # ) -> None:
    #     """
    #     保存审批审计记录。
    #     """
    #
    #     sql = """
    #     INSERT INTO wms_agent_approval_audit
    #     (
    #         thread_id,
    #         business_type,
    #         material_code,
    #         quantity,
    #         approved,
    #         approver_id,
    #         remark,
    #         approval_time
    #     )
    #     VALUES
    #     (
    #         %s,
    #         %s,
    #         %s,
    #         %s,
    #         %s,
    #         %s,
    #         %s,
    #         %s
    #     )
    #     """
    #
    #     async with self.connection.cursor() as cursor:
    #
    #         await cursor.execute(
    #             sql,
    #             (
    #                 audit.thread_id,
    #                 audit.business_type,
    #                 audit.material_code,
    #                 audit.quantity,
    #                 audit.approved,
    #                 audit.approver_id,
    #                 audit.remark,
    #                 audit.approval_time,
    #             ),
    #         )
    #
    #     await self.connection.commit()
    async def save(
            self,
            audit: ApprovalAudit,
    ) -> bool:
        """
        幂等保存审批审计。

        返回：
            True  = 本次真正插入
            False = 已存在，本次忽略
        """

        sql = """
        INSERT INTO wms_agent_approval_audit
        (
            thread_id,
            business_type,
            material_code,
            quantity,
            approved,
            approver_id,
            remark,
            approval_time
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
        ON CONFLICT
        (
            thread_id,
            business_type
        )
        DO NOTHING
        RETURNING id
        """

        async with self.connection.cursor() as cursor:
            await cursor.execute(
                sql,
                (
                    audit.thread_id,
                    audit.business_type,
                    audit.material_code,
                    audit.quantity,
                    audit.approved,
                    audit.approver_id,
                    audit.remark,
                    audit.approval_time,
                ),
            )

            row = await cursor.fetchone()

        await self.connection.commit()

        return row is not None