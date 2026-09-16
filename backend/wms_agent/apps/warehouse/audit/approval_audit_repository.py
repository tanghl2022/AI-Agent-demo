from psycopg_pool import AsyncConnectionPool
from wms_agent.apps.warehouse.audit.approval_audit import ApprovalAudit


class ApprovalAuditRepository:
    """每次操作借用连接并独立提交；连接池由基础设施管理。"""

    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def save(self, audit: ApprovalAudit) -> bool:
        sql = """
        INSERT INTO wms_agent_approval_audit
            (thread_id, business_type, material_code, quantity, approved,
             approver_id, remark, approval_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (thread_id, business_type) DO NOTHING
        RETURNING id
        """
        async with self.pool.connection() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(sql, (audit.thread_id, audit.business_type,
                    audit.material_code, audit.quantity, audit.approved,
                    audit.approver_id, audit.remark, audit.approval_time))
                row = await cursor.fetchone()
        return row is not None
