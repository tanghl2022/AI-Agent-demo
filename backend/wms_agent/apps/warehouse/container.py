from dataclasses import dataclass
from typing import Any
from .ports.inventory import InventoryPort
from .ports.location import LocationPort
from .services.wms_query_service import WmsQueryService
from .services.freeze_execution_service import FreezeExecutionService
from .audit.approval_audit_service import ApprovalAuditService
from .agent.container import create_agent_container
from .agent.service import AgentService
from .workflows.container import create_workflow_container
from .workflows.freeze_inventory.service import FreezeWorkflowService


@dataclass(frozen=True, slots=True)
class WarehouseContainer:
    """对外仅暴露仓储应用服务，不暴露连接或 Repository。"""
    agent_service: AgentService
    freeze_workflow_service: FreezeWorkflowService


def create_warehouse_container(*, inventory_client: InventoryPort, location_client: LocationPort,
    chat_model: Any, checkpointer: Any, audit_service: ApprovalAuditService) -> WarehouseContainer:

    query_service = WmsQueryService(inventory_client, location_client)
    execution_service = FreezeExecutionService(inventory_client)
    workflows = create_workflow_container(query_service=query_service,
        freeze_execution_service=execution_service, audit_service=audit_service, checkpointer=checkpointer)
    agent = create_agent_container(chat_model=chat_model, query_service=query_service,
        freeze_workflow_service=workflows.freeze_workflow_service, checkpointer=checkpointer)
    return WarehouseContainer(agent.agent_service, workflows.freeze_workflow_service)
