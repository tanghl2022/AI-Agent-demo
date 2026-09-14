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
    ) -> dict:

        if not conversation_id:
            raise ValueError(
                "conversation_id不能为空"
            )

        if not message:
            raise ValueError(
                "message不能为空"
            )

        request_id = str(
            uuid.uuid4()
        )

        initial_state = {
            "conversation_id":
                conversation_id,

            "request_id":
                request_id,

            "user_message":
                message.strip(),
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