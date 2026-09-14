from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    thread_id: str = Field(default="wms-demo-001", alias="threadId", min_length=1)


class ChatResponse(BaseModel):
    answer: str
    thread_id: str = Field(alias="threadId")
