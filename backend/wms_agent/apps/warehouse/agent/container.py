from dataclasses import dataclass
from typing import Any

from .capabilities.inventory_detail import InventoryDetailCapability
from .capabilities.location_query import LocationQueryCapability
from .capabilities.stock_query import StockQueryCapability
from .graph.builder import build_agent_main_graph
from .service import AgentService
from wms_agent.apps.warehouse.services.wms_query_service import WmsQueryService
from wms_agent.apps.warehouse.workflows.freeze_inventory.service import FreezeWorkflowService
from .tools.wms_tools import create_wms_tools
from ..subagents.inventory_analysis.agent import InventoryAnalysisSubAgent


@dataclass(frozen=True, slots=True)
class AgentContainer:
    agent_service: AgentService
    inventory_analysis_subagent: InventoryAnalysisSubAgent


def create_agent_container(
    *,
    chat_model: Any,
    query_service: WmsQueryService,
    freeze_workflow_service: FreezeWorkflowService,
    checkpointer: Any,
) -> AgentContainer:

    # ① 创建 Capability
    stock_query_capability = StockQueryCapability(
        query_service=query_service
    )

    location_query_capability = LocationQueryCapability(
        query_service=query_service
    )

    inventory_detail_capability = InventoryDetailCapability(
        query_service=query_service
    )

    # ② 基于 Capability 创建 Tool
    wms_tools = create_wms_tools(
        stock_query_capability=stock_query_capability,
        inventory_detail_capability=inventory_detail_capability,
        location_query_capability=location_query_capability,
    )

    inventory_analysis_subagent = InventoryAnalysisSubAgent(
        chat_model=chat_model,
        tools=wms_tools,
    )

    # ② Capability 注入 Graph
    graph = build_agent_main_graph(
        chat_model=chat_model,
        stock_query_capability=stock_query_capability,
        location_query_capability=location_query_capability,
        freeze_workflow_service=freeze_workflow_service,
        inventory_analysis_subagent=inventory_analysis_subagent,
        checkpointer=checkpointer,
    )

    # ③ Graph 创建 AgentService
    agent_service = AgentService(graph)

    # ④ 最终包装成 AgentContainer
    return AgentContainer(
        agent_service=agent_service,
        inventory_analysis_subagent = inventory_analysis_subagent
    )