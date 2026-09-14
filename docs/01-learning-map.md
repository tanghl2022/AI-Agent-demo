# 学习地图

本项目按“Agent 后端优先”组织，建议按以下顺序阅读：

1. `graph/state.py`：State 与消息 reducer。
2. `graph/graph_builder.py`：Node、Edge、ToolNode、Conditional Edge、InMemorySaver。
3. `tools/wms_tools.py`：Tool Calling 与业务 API 边界。
4. `services/agent_service.py`：`astream_events()` 与统一 Runtime 流。
5. `tool_execution_tracker.py`：`run_id` 对 Tool 生命周期计时。
6. `token_buffer.py`：Token batching。
7. `agent_event_factory.py`：requestId、sequence、timestamp。
8. `api/chat_controller.py`：SSE 传输层。
9. 前端：只需理解 SSE 消费、事件投影与 Timeline 展示。

下一阶段建议：数据库 Checkpoint → Session/Thread → Memory → RAG → HITL → Reliability → Evaluation。
