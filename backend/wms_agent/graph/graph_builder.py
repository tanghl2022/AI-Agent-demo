from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from wms_agent.config import settings
from wms_agent.graph.state import WmsState
from langgraph.checkpoint.base import BaseCheckpointSaver

SYSTEM_PROMPT = """
你是 WMS 仓储智能助手。

你可以根据历史对话理解上下文，例如：
- “它”
- “这个物料”
- “刚才那个托盘”
- “刚才的订单”

但历史对话中的业务数据不能默认视为当前实时数据。

对于以下可能随时间变化的 WMS 数据：
- 库存数量
- 可用库存
- 预占库存
- 冻结库存
- 当前库位
- 托盘状态
- 出库单状态
- 入库单状态
- 拣货任务状态
- 设备运行状态

只要用户询问这些数据的当前状态，
必须重新调用对应的 WMS Tool 获取最新结果，
不能只根据历史 ToolMessage 或历史 AI 回答直接作答。

历史消息只用于：
1. 理解用户上下文
2. 补全物料编码、订单号、托盘号等引用对象
3. 理解连续对话意图

实时业务事实必须以最新 Tool 查询结果为准。

如果无法确定应该查询哪个对象，
应先向用户澄清，不能编造。
"""



def build_graph(tools: list,checkpointer: BaseCheckpointSaver,):

    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key or "not-configured",
        base_url=settings.llm_base_url,
        temperature=0,
        streaming=True,
    )
    llm_with_tools = llm.bind_tools(tools)

    async def agent_node(state: WmsState):
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *state["messages"]]
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    builder = StateGraph(WmsState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode(tools))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")

    return builder.compile(checkpointer=checkpointer)
