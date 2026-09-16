import asyncio
import logging
import uuid
from contextlib import suppress
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from .dependencies import get_agent_service
from .dto.agent_stream_request import AgentStreamRequest
from wms_agent.apps.warehouse.agent.service import AgentService
from wms_agent.apps.warehouse.agent.events.event_context import set_event_publisher, reset_event_publisher
from wms_agent.apps.warehouse.agent.events.event_publisher import AgentEventPublisher
from wms_agent.apps.warehouse.agent.events.event_types import AgentEventType
from wms_agent.apps.warehouse.agent.events.sse_encoder import encode_sse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agent", tags=["Warehouse Agent"])


@router.post("/chat/stream")
@router.post("/chat/unified-stream", deprecated=True)
async def chat_stream(body: AgentStreamRequest, service: AgentService = Depends(get_agent_service)):
    request_id = str(uuid.uuid4())
    publisher = AgentEventPublisher(request_id, body.conversation_id)

    async def execute_agent():
        token = set_event_publisher(publisher)
        try:
            await publisher.publish(AgentEventType.AGENT_START, node="agent_main", status="RUNNING",
                                    data={"message": body.message})
            result = await service.chat(conversation_id=body.conversation_id, message=body.message,
                                        request_id=request_id)
            await publisher.publish(AgentEventType.DONE, node="agent_main", status=result.get("status"),
                workflow_instance_id=result.get("workflow_instance_id"),
                data={"answer": result.get("answer", ""), "intent": result.get("intent")})
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Agent 流式执行失败，request_id=%s", request_id)
            await publisher.publish(AgentEventType.SYSTEM_FAILED, node="agent_main", status="SYSTEM_FAILED",
                                    data={"message": "请求执行失败，请稍后重试"})
        finally:
            reset_event_publisher(token)
            await publisher.close()

    async def events():
        task = asyncio.create_task(execute_agent())
        try:
            while (event := await publisher.queue.get()) is not None:
                yield encode_sse(event)
        finally:
            # 断开连接后等待后台任务完成清理，避免遗留悬挂任务。
            if not task.done():
                task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
