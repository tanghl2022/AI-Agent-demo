from dataclasses import dataclass
from typing import Any

from .capabilities.location_query import LocationQueryCapability
from .capabilities.stock_query import StockQueryCapability
from .graph.builder import build_agent_main_graph
from .service import AgentService
from wms_agent.apps.warehouse.services.wms_query_service import WmsQueryService
from wms_agent.apps.warehouse.workflows.freeze_inventory.service import FreezeWorkflowService


@dataclass(frozen=True, slots=True)
class AgentContainer:
    agent_service: AgentService


def create_agent_container(
    *,
    chat_model: Any,
    query_service: WmsQueryService,
    freeze_workflow_service: FreezeWorkflowService,
    checkpointer: Any,
) -> AgentContainer:

    # ① 创建 Capability
    stock_query_capability = StockQueryCapability(
        query_service=query_service,
    )

    location_query_capability = LocationQueryCapability(
        query_service=query_service,
    )

    # ② Capability 注入 Graph
    graph = build_agent_main_graph(
        chat_model=chat_model,
        stock_query_capability=stock_query_capability,
        location_query_capability=location_query_capability,
        freeze_workflow_service=freeze_workflow_service,
        checkpointer=checkpointer,
    )

    # ③ Graph 创建 AgentService
    agent_service = AgentService(graph)

    # ④ 最终包装成 AgentContainer
    return AgentContainer(
        agent_service=agent_service
    )