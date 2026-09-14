import pytest

langgraph = pytest.importorskip("langgraph")

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph


def _build_checkpoint_graph():
    def echo(state: MessagesState):
        last = state["messages"][-1].content
        return {"messages": [AIMessage(content=f"echo:{last}")]}

    builder = StateGraph(MessagesState)
    builder.add_node("echo", echo)
    builder.add_edge(START, "echo")
    builder.add_edge("echo", END)
    return builder.compile(checkpointer=InMemorySaver())


def test_same_thread_accumulates_messages_and_other_thread_is_isolated():
    graph = _build_checkpoint_graph()
    t1 = {"configurable": {"thread_id": "thread-1"}}
    t2 = {"configurable": {"thread_id": "thread-2"}}

    graph.invoke({"messages": [HumanMessage(content="MAT001")]}, config=t1)
    state1 = graph.invoke({"messages": [HumanMessage(content="它在哪") ]}, config=t1)
    state2 = graph.invoke({"messages": [HumanMessage(content="它在哪") ]}, config=t2)

    assert len(state1["messages"]) == 4
    assert len(state2["messages"]) == 2
