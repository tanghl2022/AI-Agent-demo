import asyncio
import uuid

from wms_agent.events.agent_event import AgentEvent
from wms_agent.events.event_types import AgentEventType


class AgentEventPublisher:
    """
    当前一次Agent请求的事件发布器。

    每个HTTP请求创建一个Publisher。

    事件首先写入asyncio.Queue，
    SSE接口再不断从Queue读取并推给浏览器。
    """

    def __init__(
        self,
        request_id: str,
        conversation_id: str
    ):
        self.request_id = request_id
        self.conversation_id = conversation_id

        # 当前request内部的事件序号
        self.sequence = 0

        # SSE消费者从这里读取事件
        self.queue: asyncio.Queue = asyncio.Queue()

    async def publish(
        self,
        event_type: AgentEventType,
        *,
        node: str | None = None,
        status: str | None = None,
        workflow_instance_id: str | None = None,
        data: dict | None = None
    ) -> AgentEvent:
        """
        发布一个AgentEvent。
        """

        self.sequence += 1

        event = AgentEvent(
            eventId=str(
                uuid.uuid4()
            ),
            requestId=self.request_id,
            conversationId=self.conversation_id,
            workflowInstanceId=workflow_instance_id,
            eventType=event_type,
            node=node,
            status=status,
            sequence=self.sequence,
            data=data or {}
        )

        await self.queue.put(
            event
        )

        return event

    async def close(
        self
    ) -> None:
        """
        None作为内部流结束标记。

        None不会真正发送给前端。
        """

        await self.queue.put(
            None
        )