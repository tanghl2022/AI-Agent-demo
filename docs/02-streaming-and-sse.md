# Streaming 与 SSE

## 三个不同层次

- LLM Token/Chunk：模型生成粒度。
- SSE Event：应用协议粒度；本项目通过 TokenBuffer 将多个小 chunk 合并后发送。
- HTTP/ReadableStream chunk：网络传输粒度，不等于 SSE Event。

后端链路：`on_chat_model_stream -> TokenBuffer -> AgentEvent(TOKEN) -> StreamingResponse -> SSE`。

前端链路：`fetch -> response.body -> reader.read -> TextDecoder -> SseParser -> AgentEvent -> Vue reactive`。
