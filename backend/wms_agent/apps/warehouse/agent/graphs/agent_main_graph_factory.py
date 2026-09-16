from wms_agent.apps.warehouse.agent.graphs.agent_main_graph import (
    create_agent_main_graph,
)

from wms_agent.apps.warehouse.agent.nodes.agent.intent_recognition_node import (
    create_intent_recognition_node,
)

from wms_agent.apps.warehouse.agent.nodes.agent.parameter_validation_node import (
    validate_agent_parameters,
)
from wms_agent.apps.warehouse.agent.nodes.agent.route_event_node import (
    route_event_node
)

from wms_agent.apps.warehouse.agent.nodes.query.query_stock_node import (
    create_query_stock_node,
)

from wms_agent.apps.warehouse.agent.nodes.query.query_location_node import (
    create_query_location_node,
)

from wms_agent.apps.warehouse.agent.nodes.workflow.freeze_workflow_adapter import (
    create_freeze_workflow_adapter,
)

from wms_agent.apps.warehouse.agent.nodes.agent.clarification_node import (
    clarification_node,
)

from wms_agent.apps.warehouse.agent.nodes.agent.unknown_node import (
    unknown_node,
)
from wms_agent.apps.warehouse.agent.nodes.agent.context_merge_node import (
    merge_agent_context,
)

def build_agent_main_graph(
    *,
    chat_model,
    query_service,
    freeze_workflow_service,
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
            query_service
        )
    )

    # ========================================================
    # 3. Location Query Node
    # ========================================================

    location_node = (
        create_query_location_node(
            query_service
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
        checkpointer,
    )
