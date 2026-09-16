from dataclasses import dataclass
from typing import Any
from .graphs.agent_main_graph_factory import build_agent_main_graph
from .service import AgentService
from wms_agent.apps.warehouse.services.wms_query_service import WmsQueryService
from wms_agent.apps.warehouse.workflows.freeze_inventory.service import FreezeWorkflowService


@dataclass(frozen=True, slots=True)
class AgentContainer:
    agent_service: AgentService


def create_agent_container(*, chat_model: Any, query_service: WmsQueryService,
    freeze_workflow_service: FreezeWorkflowService, checkpointer: Any) -> AgentContainer:
    """主图借用外部能力，仅在这里确定节点装配关系。"""
    graph = build_agent_main_graph(chat_model=chat_model, query_service=query_service,
                                  freeze_workflow_service=freeze_workflow_service, checkpointer=checkpointer)
    return AgentContainer(AgentService(graph))
