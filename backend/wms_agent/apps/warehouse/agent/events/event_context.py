from contextvars import ContextVar, Token

from wms_agent.apps.warehouse.agent.events.event_publisher import (
    AgentEventPublisher
)


_current_event_publisher: ContextVar[
    AgentEventPublisher | None
] = ContextVar(
    "current_agent_event_publisher",
    default=None
)


def set_event_publisher(
    publisher: AgentEventPublisher
) -> Token:
    """
    将Publisher绑定到当前异步执行上下文。
    """

    return _current_event_publisher.set(
        publisher
    )


def get_event_publisher(
) -> AgentEventPublisher | None:
    """
    Node可以通过这个方法获得当前请求的Publisher。
    """

    return _current_event_publisher.get()


def reset_event_publisher(
    token: Token
) -> None:
    """
    请求结束必须恢复ContextVar，
    防止上下文残留。
    """

    _current_event_publisher.reset(
        token
    )