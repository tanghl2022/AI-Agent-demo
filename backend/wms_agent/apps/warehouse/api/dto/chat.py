from pydantic import AliasChoices, BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str = Field(
        validation_alias=AliasChoices("conversationId", "conversation_id", "threadId", "thread_id"),
        serialization_alias="conversationId", min_length=1,
    )

    @property
    def thread_id(self) -> str:
        """保留旧客户端的会话字段读取方式。"""
        return self.conversation_id


class ChatResponse(BaseModel):
    conversation_id: str = Field(alias="conversationId")
    workflow_instance_id: str | None = Field(default=None, alias="workflowInstanceId")
    intent: str | None = None
    status: str
    answer: str
    active_workflow: str | None = Field(default=None, alias="activeWorkflow")
    model_config = {"populate_by_name": True}
