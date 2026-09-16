from wms_agent.apps.warehouse.agent.models.agent_event import AgentEventType
from wms_agent.apps.warehouse.agent.agent_event_factory import AgentEventFactory


def test_event_sequence_increments():
    factory = AgentEventFactory(request_id="req-1")
    first = factory.create(AgentEventType.START, {})
    second = factory.create(AgentEventType.DONE, {})
    assert first.request_id == second.request_id == "req-1"
    assert (first.sequence, second.sequence) == (1, 2)
