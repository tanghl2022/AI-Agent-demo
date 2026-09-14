import asyncio
import uuid

from fastapi import (
    APIRouter,
    Request
)

from fastapi.responses import (
    StreamingResponse
)

from wms_agent.api.dto.agent_stream_request import (
    AgentStreamRequest
)

from wms_agent.events.event_context import (
    set_event_publisher,
    reset_event_publisher
)

from wms_agent.events.event_publisher import (
    AgentEventPublisher
)

from wms_agent.events.event_types import (
    AgentEventType
)

from wms_agent.events.sse_encoder import (
    encode_sse
)


router = APIRouter(
    prefix="/api",
    tags=[
        "WMS "
    ],
)



@router.post(
    "/agent/chat/stream"
)
async def chat_stream(
    request_body: AgentStreamRequest,
    request: Request
):

    # ========================================
    # 一次HTTP请求一个requestId
    # ========================================

    request_id = str(
        uuid.uuid4()
    )

    publisher = AgentEventPublisher(
        request_id=
            request_id,
        conversation_id=
            request_body.conversation_id
    )

    service = (
        request.app.state.agent_service
    )

    # ========================================
    # 后台执行Main Graph
    # ========================================

    async def execute_agent():

        context_token = (
            set_event_publisher(
                publisher
            )
        )

        try:

            # =================================
            # Agent Start
            # =================================

            await publisher.publish(
                AgentEventType.AGENT_START,
                node="agent_main",
                status="RUNNING",
                data={
                    "message":
                        request_body.message
                }
            )

            result = await service.chat(
                conversation_id=
                    request_body.conversation_id,

                message=
                    request_body.message
            )

            # =================================
            # Done
            # =================================

            await publisher.publish(
                AgentEventType.DONE,
                node="agent_main",
                status=result.get(
                    "status"
                ),
                workflow_instance_id=
                    result.get(
                        "workflow_instance_id"
                    ),
                data={
                    "answer":
                        result.get(
                            "answer",
                            ""
                        ),

                    "intent":
                        result.get(
                            "intent"
                        )
                }
            )

        except asyncio.CancelledError:

            raise

        except Exception as exc:

            await publisher.publish(
                AgentEventType.SYSTEM_FAILED,
                node="agent_main",
                status="SYSTEM_FAILED",
                data={
                    "message":
                        str(exc)
                }
            )

        finally:

            reset_event_publisher(
                context_token
            )

            await publisher.close()

    # ========================================
    # SSE Generator
    # ========================================

    async def event_generator():

        task = asyncio.create_task(
            execute_agent()
        )

        try:

            while True:

                event = await (
                    publisher.queue.get()
                )

                if event is None:
                    break

                yield encode_sse(
                    event
                )

        finally:

            # 浏览器主动断开连接时，
            # 不再继续执行无意义的SSE推送任务。
            if not task.done():

                task.cancel()

    return StreamingResponse(
        event_generator(),
        media_type=
            "text/event-stream",
        headers={
            "Cache-Control":
                "no-cache",

            # Nginx代理SSE时非常重要，
            # 禁止代理缓冲。
            "X-Accel-Buffering":
                "no"
        }
    )