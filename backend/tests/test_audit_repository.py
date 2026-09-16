"""审计写入必须使用池连接和参数化 SQL，并返回幂等插入结果。"""
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pytest

from wms_agent.apps.warehouse.audit.approval_audit import ApprovalAudit
from wms_agent.apps.warehouse.audit.approval_audit_repository import ApprovalAuditRepository


@pytest.mark.parametrize("row, expected", [((7,), True), (None, False)])
async def test_audit_write_uses_independent_connection_scope(row, expected):
    calls = []

    class Cursor:
        async def execute(self, sql, params):
            calls.append((sql, params))

        async def fetchone(self):
            return row

    class Connection:
        @asynccontextmanager
        async def cursor(self):
            yield Cursor()

    class Pool:
        @asynccontextmanager
        async def connection(self):
            calls.append("acquired")
            try:
                yield Connection()
            finally:
                calls.append("returned")

    now = datetime.now(timezone.utc)
    audit = ApprovalAudit(thread_id="freeze-1", business_type="FREEZE_INVENTORY",
        material_code="MAT001", quantity=3, approved=True, approver_id="U1",
        remark="盘点", approval_time=now)
    assert await ApprovalAuditRepository(Pool()).save(audit) is expected
    assert calls[0] == "acquired"
    assert calls[-1] == "returned"
    sql, params = calls[1]
    assert "ON CONFLICT (thread_id, business_type) DO NOTHING" in sql
    assert params == ("freeze-1", "FREEZE_INVENTORY", "MAT001", 3, True, "U1", "盘点", now)
