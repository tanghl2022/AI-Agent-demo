from typing import Any

from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from wms_agent.apps.warehouse.agent.models.agent_state import (
    AgentState,
)


from wms_agent.apps.warehouse.agent.nodes.agent.agent_router import (
    route_agent_request,
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
):

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
