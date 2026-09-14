from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    """
    WMS Agent统一聊天入口请求。
    """

    thread_id: str = Field(
        alias="threadId",
        min_length=1,
    )

    message: str = Field(
        min_length=1,
    )

    model_config = {
        "populate_by_name": True
    }