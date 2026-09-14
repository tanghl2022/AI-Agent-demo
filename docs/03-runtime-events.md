# LangGraph Runtime Events

`stream_mode="updates"` 关注 Node 对 State 的更新；`stream_mode="messages"` 关注 LLM MessageChunk；`astream_events()` 关注 Runtime 生命周期。

本项目使用 `astream_events()`：

- `on_tool_start` -> TOOL_START，同时 `ToolExecutionTracker.start(run_id)`。
- `on_tool_end` -> TOOL_END，同时 `finish(run_id)` 得到独立 Tool 耗时。
- `on_chat_model_stream` -> TOKEN。

这避免了从 `tools` Node 的 updates 推导 Tool 结束时间时出现“并行 Tool 耗时都等于最慢 Tool”的问题。
