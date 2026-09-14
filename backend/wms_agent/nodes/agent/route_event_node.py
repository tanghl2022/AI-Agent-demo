from wms_agent.events.event_context import (
    get_event_publisher
)

from wms_agent.events.event_types import (
    AgentEventType
)
from wms_agent.nodes.agent.agent_router import route_agent_request


async def route_event_node(
    state: dict
) -> dict:
    """
    只负责发布Router事件。

    真正的路由判断仍然由
    route_agent_request()
    完成。
    """

    route = route_agent_request(
        state
    )

    publisher = get_event_publisher()

    if publisher:

        await publisher.publish(
            AgentEventType.ROUTE,
            node="router",
            status="SUCCESS",
            data={
                "route":
                    route,

                "intent":
                    state.get(
                        "intent"
                    )
            }
        )

    return {}