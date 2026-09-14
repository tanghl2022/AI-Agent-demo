from datetime import datetime

from wms_agent.graphs.freeze_inventory_workflow import (
    build_approval_result,
    route_after_approval,
)


def test_build_approval_result_should_build_approved_state():
    """
    人工批准后，应该生成完整审批状态。
    """
    resume_data = {
        "approved": True,
        "approverId": "U10086",
        "remark": "盘点异常，批准冻结",
    }

    result = build_approval_result(resume_data)

    assert result["approved"] is True
    assert result["approver_id"] == "U10086"
    assert result["approval_remark"] == "盘点异常，批准冻结"
    assert result["status"] == "APPROVED"

    # 审批时间由后端生成
    assert result["approval_time"] is not None
    datetime.fromisoformat(result["approval_time"])


def test_build_approval_result_should_build_rejected_state():
    """
    人工拒绝后，也必须记录审批人和意见。
    """
    resume_data = {
        "approved": False,
        "approverId": "U10087",
        "remark": "冻结原因不充分",
    }

    result = build_approval_result(resume_data)

    assert result["approved"] is False
    assert result["approver_id"] == "U10087"
    assert result["approval_remark"] == "冻结原因不充分"
    assert result["status"] == "REJECTED"


def test_route_after_approval_should_execute_when_approved():
    state = {
        "approved": True
    }

    assert route_after_approval(state) == "execute"


def test_route_after_approval_should_cancel_when_rejected():
    state = {
        "approved": False
    }

    assert route_after_approval(state) == "cancel"
