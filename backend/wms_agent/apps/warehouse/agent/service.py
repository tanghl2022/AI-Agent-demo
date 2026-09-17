import uuid
from typing import Any


class AgentService:

    def __init__(
        self,
        agent_graph: Any,
    ):
        self.agent_graph = (
            agent_graph
        )

    async def chat(
        self,
        conversation_id: str,
        message: str,
        *,
        request_id: str | None = None,
    ) -> dict:

        if not conversation_id.strip():
            raise ValueError(
                "conversation_id不能为空"
            )

        if not message.strip():
            raise ValueError(
                "message不能为空"
            )

        request_id = request_id or str(
            uuid.uuid4()
        )

        initial_state = {
            "conversation_id":
                conversation_id,

            "request_id":
                request_id,

            "user_message":
                message.strip(),

            # 每一轮请求都重新决定是否创建业务流程。
            # 不能从会话 Checkpoint 继承上一次已经结束或等待审批的实例。
            "workflow_instance_id":
                None,

            "active_workflow":
                None,
        }

        config = {
            "configurable": {
                # LangGraph仍然要求字段名thread_id
                # 但这里它的业务语义已经是conversation_id
                "thread_id":
                    conversation_id,
            }
        }

        return (
            await self.agent_graph.ainvoke(
                initial_state,
                config=config,
            )
        )

    async def get_checkpoint_state(self, thread_id: str) -> dict:
        """将快照转换为 HTTP 可序列化的调试数据。"""
        snapshot = await self.agent_graph.aget_state({"configurable": {"thread_id": thread_id}})
        return {"threadId": thread_id, "values": snapshot.values,
                "next": list(snapshot.next), "createdAt": snapshot.created_at}

    async def get_checkpoint_history(self, thread_id: str) -> list[dict]:
        """限制单次读取数量，避免历史无限增长导致响应过大。"""
        return [{"values": snapshot.values, "next": list(snapshot.next),
                 "createdAt": snapshot.created_at}
                async for snapshot in self.agent_graph.aget_state_history(
                    {"configurable": {"thread_id": thread_id}}, limit=100)]
