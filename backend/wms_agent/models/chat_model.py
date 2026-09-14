from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str

    conversation_id: str = Field(
        alias="conversationId",
        min_length=1,
    )

    model_config = {
        "populate_by_name": True
    }


class ChatResponse(BaseModel):

    conversation_id: str = Field(
        alias="conversationId"
    )

    workflow_instance_id: str | None = Field(
        default=None,
        alias="workflowInstanceId"
    )

    intent: str | None = None

    status: str

    answer: str

    active_workflow: str | None = Field(
        default=None,
        alias="activeWorkflow"
    )

    model_config = {
        "populate_by_name": True
    }
