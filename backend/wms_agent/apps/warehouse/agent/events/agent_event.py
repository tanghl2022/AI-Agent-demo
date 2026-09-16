from datetime import (
    datetime,
    timezone,
)

from typing import Any

from pydantic import (
    BaseModel,
    Field,
)

from wms_agent.apps.warehouse.agent.events.event_types import (
    AgentEventType,
)


class AgentEvent(BaseModel):

    event_id: str = Field(
        alias="eventId"
    )

    request_id: str = Field(
        alias="requestId"
    )

    conversation_id: str = Field(
        alias="conversationId"
    )

    workflow_instance_id: (
        str | None
    ) = Field(
        default=None,
        alias="workflowInstanceId",
    )

    event_type: AgentEventType = Field(
        alias="eventType"
    )

    node: str | None = None

    status: str | None = None

    sequence: int

    timestamp: str = Field(
        default_factory=lambda: (
            datetime.now(
                timezone.utc
            ).isoformat()
        )
    )

    data: dict[str, Any] = (
        Field(
            default_factory=dict
        )
    )

    model_config = {
        "populate_by_name": True
    }
