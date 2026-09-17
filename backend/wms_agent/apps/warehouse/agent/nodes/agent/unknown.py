from wms_agent.apps.warehouse.agent.state.agent_state import (
    AgentState,
)


def unknown_node(
    state: AgentState,
) -> dict:
    """
    UNKNOWN兜底节点。

    这里不调用任何Tool，
    更不会执行WMS写操作。
    """

    answer = state.get("answer")

    if answer:

        return {}

    return {
        "status": "UNKNOWN",

        "answer":
            "我暂时无法识别这个WMS业务请求。"
            "当前支持库存查询、库位查询和库存冻结。",
    }