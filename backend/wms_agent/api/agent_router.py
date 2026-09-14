from fastapi import (
    APIRouter,
    Depends,
)

from wms_agent.api.dto.agent_chat_request import (
    AgentChatRequest,
)

from wms_agent.api.dto.agent_chat_response import (
    AgentChatResponse,
)

from wms_agent.services.agent_service import (
    AgentService,
)


router = APIRouter(
    prefix="/api/agent",
    tags=["WMS Agent"],
)


# ============================================================
# 这里后续会由application.py统一注入
# ============================================================

_agent_service: AgentService | None = None


def set_agent_service(
    service: AgentService,
):
    """
    注册AgentService。

    当前Demo采用显式注入。

    后续项目复杂后可以改成：
        FastAPI Depends
        dependency-injector
        application container
    """

    global _agent_service

    _agent_service = service


def get_agent_service() -> AgentService:

    if _agent_service is None:

        raise RuntimeError(
            "AgentService尚未初始化"
        )

    return _agent_service


@router.post(
    "/chat",
    response_model=AgentChatResponse,
    response_model_by_alias=True,
)
async def agent_chat(
    request: AgentChatRequest,
    agent_service: AgentService = Depends(
        get_agent_service
    ),
):
    """
    WMS Agent统一自然语言入口。
    """

    result = await agent_service.chat(
        thread_id=request.thread_id,
        message=request.message,
    )

    return AgentChatResponse(
        thread_id=request.thread_id,

        intent=result.get(
            "intent"
        ),

        status=result.get(
            "status",
            "UNKNOWN",
        ),

        answer=result.get(
            "answer",
            "",
        ),

        active_workflow=result.get(
            "active_workflow"
        ),
    )