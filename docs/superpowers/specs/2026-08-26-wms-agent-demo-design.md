# WMS Agent Demo Design

## Goal

Build a deployable and study-friendly WMS Agent demo that consolidates the capabilities learned so far: LangGraph state/node/edge, tool calling, parallel tools, runtime events, unified AgentEvent, SSE, token batching, Vue timeline, tool timing, and InMemory checkpoint with thread isolation.

## Scope

- Backend: Python, FastAPI, LangGraph, OpenAI-compatible ChatModel.
- Frontend: Vue 3 + TypeScript + Vite, used mainly for visualization.
- WMS: built-in mock query service; no external WMS dependency required.
- Checkpoint: InMemorySaver only in this version.
- Excluded: PostgreSQL checkpointer, RAG, long-term memory, HITL, write tools, Redis/MQ.

## Architecture

Vue sends a chat request containing `message` and `threadId` to FastAPI. The backend runs a LangGraph ReAct-style loop (`agent -> tools -> agent`) compiled with `InMemorySaver`. `AgentService.unified_stream()` listens to `astream_events()` and normalizes runtime events into `AgentEvent` values: START, STATUS, TOOL_START, TOOL_END, TOKEN, ERROR, DONE. FastAPI emits these values as SSE. Vue parses the SSE stream, appends TOKEN content to the assistant message, and projects Tool lifecycle events into an execution timeline.

## Backend modules

- `graph/state.py`: LangGraph message state.
- `graph/graph_builder.py`: binds tools, builds the graph, and enables checkpointing.
- `tools/wms_tools.py`: LangChain tools backed by mock WMS service.
- `services/wms_query_service.py`: deterministic WMS mock data and controlled delays.
- `services/agent_service.py`: non-stream and unified runtime stream execution.
- `services/agent_event_factory.py`: request-scoped AgentEvent sequence/timestamp factory.
- `services/token_buffer.py`: size/time based token batching.
- `services/tool_execution_tracker.py`: run_id -> start time tracking.
- `api/chat_controller.py`: REST + SSE transport only.

## Event protocol

Every SSE data payload is a complete AgentEvent:

```json
{
  "event": "TOKEN",
  "requestId": "...",
  "sequence": 10,
  "timestamp": "...",
  "data": {"content": "..."}
}
```

Supported events: START, STATUS, TOOL_START, TOOL_END, TOKEN, ERROR, DONE.

## Checkpoint behavior

The graph is compiled once with `InMemorySaver`. Each invocation passes:

```python
{"configurable": {"thread_id": thread_id}}
```

Same `thread_id` restores prior message state; different IDs are isolated. Restarting the Python process loses checkpoints by design.

## Safety boundary

This demo contains read-only WMS query tools. No LLM path writes inventory or executes warehouse control actions. Future write operations must go through controlled WMS APIs with authorization, validation, idempotency, state machine checks and human approval.

## Validation

- Unit tests for TokenBuffer, ToolExecutionTracker, AgentEventFactory.
- API health test.
- Checkpoint test proving same thread retains history and separate thread does not share state.
- Frontend build check.
- Docker Compose definitions for backend and frontend.
