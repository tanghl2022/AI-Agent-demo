import time
import uuid
from datetime import datetime, timezone
from typing import Any

from wms_agent.apps.warehouse.agent.models.agent_event import AgentEvent, AgentEventType


class AgentEventFactory:
    """为一次请求生成统一 requestId、sequence、timestamp。"""

    def __init__(self, request_id: str | None = None, clock=time.perf_counter):
        self.request_id = request_id or str(uuid.uuid4())
        self._sequence = 0
        self._clock = clock
        self._started_at = self._clock()

    def create(self, event: AgentEventType, data: dict[str, Any]) -> AgentEvent:
        self._sequence += 1
        return AgentEvent(
            event=event,
            requestId=self.request_id,
            sequence=self._sequence,
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            data=data,
        )

    def elapsed_ms(self) -> int:
        return max(0, int((self._clock() - self._started_at) * 1000))
