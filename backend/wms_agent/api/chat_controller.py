from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from wms_agent.models.chat_model import ChatRequest, ChatResponse

router = APIRouter(prefix="/api", tags=["WMS Agent"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "wms-agent-demo"}


@router.post(
    "/agent/chat",
    response_model=ChatResponse
)
async def chat(
    request_body: ChatRequest,
    request: Request
) -> ChatResponse:

    service = (
        request.app.state.agent_service
    )

    result = await service.chat(
        conversation_id=request_body.conversation_id,
        message=request_body.message,
    )

    return ChatResponse(
        conversationId=
            request_body.conversation_id,

        workflowInstanceId=
            result.get(
                "workflow_instance_id"
            ),

        intent=
            result.get(
                "intent"
            ),

        status=
            result.get(
                "status",
                "UNKNOWN"
            ),

        answer=
            result.get(
                "answer",
                ""
            ),

        activeWorkflow=
            result.get(
                "active_workflow"
            ),
    )


@router.post("/agent/chat/unified-stream")
async def chat_unified_stream(request_body: ChatRequest, request: Request):
    service = request.app.state.agent_service

    async def event_generator():
        async for event in service.unified_stream(request_body.message, request_body.thread_id):
            yield f"event: {event.event.value}\ndata: {event.model_dump_json(by_alias=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@router.get(
    "/agent/checkpoint/{thread_id}"
)
async def get_checkpoint(
    thread_id: str,
    request: Request,
):
    """
    查看指定thread_id当前最新Checkpoint。

    仅用于Demo学习和调试。
    """

    agent_service = (
        request
        .app
        .state
        .agent_service
    )

    return await agent_service.get_checkpoint_state(thread_id)

@router.get(
    "/agent/checkpoint/{thread_id}/history"
)
async def get_checkpoint_history(
    thread_id: str,
    request: Request,
):
    """
    查询指定Thread的全部历史Checkpoint。

    用于学习和调试LangGraph状态持久化机制。
    """

    agent_service = (
        request
        .app
        .state
        .agent_service
    )

    return await agent_service.get_checkpoint_history(thread_id)
