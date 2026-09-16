from fastapi import Request
from wms_agent.apps.warehouse.agent.service import AgentService
from wms_agent.apps.warehouse.workflows.freeze_inventory.service import FreezeWorkflowService


def get_agent_service(request: Request) -> AgentService:
    """HTTP 层获取运行时的唯一入口，无模块全局服务实例。"""
    return request.app.state.runtime.warehouse.agent_service


def get_freeze_service(request: Request) -> FreezeWorkflowService:
    return request.app.state.runtime.warehouse.freeze_workflow_service
