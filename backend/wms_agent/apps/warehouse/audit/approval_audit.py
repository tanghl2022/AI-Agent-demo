from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ApprovalAudit:
    """
    人工审批审计记录。

    这是业务审计数据，
    不等同于 LangGraph Checkpoint。
    """

    thread_id: str
    business_type: str

    material_code: str
    quantity: int

    approved: bool

    approver_id: str
    remark: str

    approval_time: datetime