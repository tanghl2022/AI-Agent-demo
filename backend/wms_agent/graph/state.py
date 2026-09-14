from langgraph.graph import MessagesState


class WmsState(MessagesState):
    """消息字段由 LangGraph 的 add_messages reducer 自动累积。"""

    pass
