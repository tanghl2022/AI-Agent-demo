from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class AgentEventType(str, Enum):
    START = "START"
    STATUS = "STATUS"
    TOOL_START = "TOOL_START"
    TOOL_END = "TOOL_END"
    TOKEN = "TOKEN"
    ERROR = "ERROR"
    DONE = "DONE"


class AgentEvent(BaseModel):
    """统一前后端 Agent SSE 事件协议。"""

    model_config = ConfigDict(populate_by_name=True)

    event: AgentEventType
    request_id: str = Field(alias="requestId")
    sequence: int
    timestamp: str
    data: dict[str, Any]
