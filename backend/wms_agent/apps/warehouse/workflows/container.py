from dataclasses import dataclass
from typing import Any
from wms_agent.apps.warehouse.services.wms_query_service import WmsQueryService
from wms_agent.apps.warehouse.services.freeze_execution_service import FreezeExecutionService
from wms_agent.apps.warehouse.audit.approval_audit_service import ApprovalAuditService
from .freeze_inventory.graph import build_freeze_inventory_workflow
from .freeze_inventory.service import FreezeWorkflowService


@dataclass(frozen=True, slots=True)
class WorkflowContainer:
    freeze_workflow_service: FreezeWorkflowService


def create_workflow_container(*, query_service: WmsQueryService,
    freeze_execution_service: FreezeExecutionService, audit_service: ApprovalAuditService,
    checkpointer: Any) -> WorkflowContainer:
    """仅装配工作流，不拥有数据库或外部系统连接。"""
    graph = build_freeze_inventory_workflow(query_service, audit_service, freeze_execution_service, checkpointer)
    return WorkflowContainer(FreezeWorkflowService(graph))
