from fastapi import APIRouter, Depends, HTTPException
from .dependencies import get_agent_service
from .dto.chat import ChatRequest, ChatResponse
from wms_agent.apps.warehouse.agent.service import AgentService

router = APIRouter(prefix="/api/agent", tags=["Warehouse Agent"])


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, service: AgentService = Depends(get_agent_service)) -> ChatResponse:
    try:
        result = await service.chat(conversation_id=body.conversation_id, message=body.message)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ChatResponse(conversationId=body.conversation_id,
        workflowInstanceId=result.get("workflow_instance_id"), intent=result.get("intent"),
        status=result.get("status", "UNKNOWN"), answer=result.get("answer", ""),
        activeWorkflow=result.get("active_workflow"))


@router.get("/checkpoint/{thread_id}")
async def checkpoint(thread_id: str, service: AgentService = Depends(get_agent_service)):
    return await service.get_checkpoint_state(thread_id)


@router.get("/checkpoint/{thread_id}/history")
async def checkpoint_history(thread_id: str, service: AgentService = Depends(get_agent_service)):
    return await service.get_checkpoint_history(thread_id)
