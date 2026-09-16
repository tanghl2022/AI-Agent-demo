import pytest

from wms_agent.apps.warehouse.audit.approval_audit import ApprovalAudit


def test_same_workflow_should_have_same_audit_business_key():
    """
    同一个 thread + business_type
    应代表同一次业务审批。

    后续数据库唯一约束就基于这两个字段。
    """

    audit = ApprovalAudit(
        thread_id="freeze-idem-001",
        business_type="FREEZE_INVENTORY",
        material_code="MAT001",
        quantity=20,
        approved=True,
        approver_id="U10001",
        remark="批准",
        approval_time=None,
    )

    business_key = (
        f"{audit.thread_id}:"
        f"{audit.business_type}"
    )

    assert business_key == (
        "freeze-idem-001:"
        "FREEZE_INVENTORY"
    )