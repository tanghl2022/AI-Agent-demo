import json

from wms_agent.events.agent_event import AgentEvent


def encode_sse(
    event: AgentEvent
) -> str:
    """
    将AgentEvent转换为标准SSE文本格式。

    SSE格式：

    event: tool_start
    data: {...}

    注意最后必须有两个换行。
    """

    payload = event.model_dump(
        by_alias=True,
        mode="json"
    )

    json_text = json.dumps(
        payload,
        ensure_ascii=False
    )

    return (
        f"event: {event.event_type.value}\n"
        f"data: {json_text}\n\n"
    )