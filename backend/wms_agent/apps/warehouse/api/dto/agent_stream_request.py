from .chat import ChatRequest


class AgentStreamRequest(ChatRequest):
    """流式和非流式请求使用同一套会话字段契约。"""
