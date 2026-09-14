from pydantic import (
    BaseModel,
    Field
)


class AgentStreamRequest(
    BaseModel
):

    conversation_id: str = Field(
        alias="conversationId",
        min_length=1
    )

    message: str = Field(
        min_length=1
    )

    model_config = {
        "populate_by_name": True
    }