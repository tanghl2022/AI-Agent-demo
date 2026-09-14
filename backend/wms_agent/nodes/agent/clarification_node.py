from wms_agent.models.agent_state import (
    AgentState,
)


def clarification_node(
    state: AgentState,
) -> dict:
    """
    参数补充节点。

    Parameter Validation已经生成了具体补问内容，
    所以这里原则上不重新调用LLM。

    例如：

        用户：
        帮我冻结MAT001

        Validation：
        quantity缺失

        answer：
        你希望冻结MAT001多少数量？

    当前V6.0只负责返回补问，
    暂不实现多轮参数恢复。
    """

    answer = state.get("answer")

    if answer:

        return {}

    return {
        "status":
            "CLARIFICATION_REQUIRED",

        "answer":
            "当前请求缺少必要参数，请补充后重新提交。",
    }
