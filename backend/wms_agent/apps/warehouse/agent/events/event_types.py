from enum import Enum


class AgentEventType(
    str,
    Enum,
):

    AGENT_START = (
        "agent_start"
    )

    INTENT_START = (
        "intent_start"
    )

    INTENT_RESULT = (
        "intent_result"
    )

    PARAMETER_VALIDATION = (
        "parameter_validation"
    )

    ROUTE = (
        "route"
    )

    TOOL_START = (
        "tool_start"
    )

    TOOL_END = (
        "tool_end"
    )

    WORKFLOW_START = (
        "workflow_start"
    )

    APPROVAL_REQUIRED = (
        "approval_required"
    )

    APPROVAL_RESULT = (
        "approval_result"
    )

    RETRY = (
        "retry"
    )

    TOKEN = (
        "token"
    )

    BUSINESS_FAILED = (
        "business_failed"
    )

    SYSTEM_FAILED = (
        "system_failed"
    )

    DONE = (
        "done"
    )