from pydantic import BaseModel, Field


class AgentChatResponse(BaseModel):
    """
    WMS Agent统一响应。

    V6.0暂时返回最核心字段。
    后面V6.x再增加：
        workflowInstanceId
        events
        toolCalls
        evidence
        confidence
        approvalInfo
    """

    thread_id: str = Field(
        alias="threadId"
    )

    intent: str | None = None

    status: str

    answer: str

    active_workflow: str | None = Field(
        default=None,
        alias="activeWorkflow",
    )

    model_config = {
        "populate_by_name": True
    }