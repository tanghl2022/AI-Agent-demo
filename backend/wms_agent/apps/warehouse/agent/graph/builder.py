from typing import Any

from wms_agent.apps.warehouse.agent.nodes.agent.intent_recognition import (
    create_intent_recognition_node,
)
from wms_agent.apps.warehouse.agent.nodes.agent.inventory_analysis import InventoryAnalysisNode

from wms_agent.apps.warehouse.agent.nodes.agent.parameter_validation import (
    validate_agent_parameters,
)
from wms_agent.apps.warehouse.agent.nodes.agent.route_event import (
    route_event_node
)


from wms_agent.apps.warehouse.agent.capabilities.freeze_workflow import (
    create_freeze_workflow_adapter,
)

from wms_agent.apps.warehouse.agent.nodes.agent.clarification import (
    clarification_node,
)

from wms_agent.apps.warehouse.agent.nodes.agent.unknown import (
    unknown_node,
)
from wms_agent.apps.warehouse.agent.nodes.agent.context_merge import (
    merge_agent_context,
)


from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from wms_agent.apps.warehouse.agent.nodes.query.query_location import create_query_location_node
from wms_agent.apps.warehouse.agent.nodes.query.query_stock import create_query_stock_node
from wms_agent.apps.warehouse.agent.state.agent_state import (
    AgentState,
)


from wms_agent.apps.warehouse.agent.graph.routers import (
    route_agent_request,
)

def build_agent_main_graph(
    *,
    chat_model,
    stock_query_capability,
    location_query_capability,
    freeze_workflow_service,
    inventory_analysis_subagent,
    checkpointer,
):
    """
    创建正式运行的WMS Agent Main Graph。

    这里负责依赖装配，
    类似Spring @Configuration。
    """

    # ========================================================
    # 1. Intent Node
    # ========================================================

    intent_node = (
        create_intent_recognition_node(
            chat_model
        )
    )

    # ========================================================
    # 2. Stock Query Node
    # ========================================================

    stock_node = (
        create_query_stock_node(
            stock_query_capability
        )
    )

    # ========================================================
    # 3. Location Query Node
    # ========================================================

    location_node = (
        create_query_location_node(
            location_query_capability
        )
    )

    # ========================================================
    # 4. Freeze Workflow Adapter
    # ========================================================

    freeze_node = (
        create_freeze_workflow_adapter(
            freeze_workflow_service
        )
    )

    inventory_analysis_node = InventoryAnalysisNode(
        subagent=inventory_analysis_subagent,
    )

    # ========================================================
    # 5. Main Graph
    # ========================================================

    return create_agent_main_graph(

        intent_recognition_node=
        intent_node,

        context_merge_node=
        merge_agent_context,

        validate_parameters_node=
        validate_agent_parameters,

        inventory_analysis_node=
        inventory_analysis_node,

        route_event_node=
        route_event_node,

        query_stock_node=
        stock_node,

        query_location_node=
        location_node,

        freeze_inventory_node=
        freeze_node,

        clarification_node=
        clarification_node,

        unknown_node=
        unknown_node,

        checkpointer=
        checkpointer

    )


def create_agent_main_graph(
    intent_recognition_node: Any,
    context_merge_node: Any,
    validate_parameters_node: Any,
    route_event_node:Any,
    query_stock_node: Any,
    query_location_node: Any,
    freeze_inventory_node: Any,
    clarification_node: Any,
    unknown_node: Any,
    checkpointer=None,
    inventory_analysis_node=Any):

    builder = StateGraph(
        AgentState
    )

    builder.add_node(
        "intent_recognition",
        intent_recognition_node,
    )

    builder.add_node(
        "context_merge",
        context_merge_node,
    )

    builder.add_node(
        "validate_parameters",
        validate_parameters_node,
    )
    builder.add_node(
        "route_event",
        route_event_node,
    )
    builder.add_node(
        "query_stock",
        query_stock_node,
    )

    builder.add_node(
        "query_location",
        query_location_node,
    )

    builder.add_node(
        "freeze_inventory",
        freeze_inventory_node,
    )

    builder.add_node(
        "clarification",
        clarification_node,
    )

    builder.add_node(
        "inventory_analysis",
        inventory_analysis_node,
    )

    builder.add_node(
        "unknown",
        unknown_node,
    )

    builder.add_edge(
        START,
        "intent_recognition",
    )

    builder.add_edge(
        "intent_recognition",
        "context_merge",
    )

    builder.add_edge(
        "context_merge",
        "validate_parameters",
    )

    builder.add_edge(
        "validate_parameters",
        "route_event",
    )

    builder.add_conditional_edges(
        "route_event",
        route_agent_request,
        {
            "query_stock":
                "query_stock",

            "query_location":
                "query_location",

            "freeze_inventory":
                "freeze_inventory",

            "inventory_analysis":
                "inventory_analysis",

            "clarification":
                "clarification",

            "unknown":
                "unknown"
        }
    )

    builder.add_edge(
        "query_stock",
        END,
    )

    builder.add_edge(
        "query_location",
        END,
    )

    builder.add_edge(
        "freeze_inventory",
        END,
    )
    builder.add_edge(
        "inventory_analysis",
        END
    )
    builder.add_edge(
        "clarification",
        END,
    )

    builder.add_edge(
        "unknown",
        END,
    )

    if checkpointer is None:
        return builder.compile()

    return builder.compile(
        checkpointer=checkpointer
    )
