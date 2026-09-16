# WMS Agent Demo

> 后端已迁移为业务应用与外部系统接入分离的结构。当前目录、启动配置、数据库初始化和测试方式以 [backend/README.md](backend/README.md) 为准；下文保留早期学习示例。

这是根据前期学习过程整理的一套 **后端优先、可部署、可继续扩展** 的 WMS Agent 学习项目。

## 已包含能力

- LangGraph `State / Node / Edge / Conditional Edge`
- Tool Calling：库存、库存明细、库位查询
- 多 Tool 并行执行
- `astream_events()` Runtime 事件
- `on_tool_start / on_tool_end / on_chat_model_stream`
- Tool 独立耗时追踪
- 统一 AgentEvent：`START / STATUS / TOOL_START / TOOL_END / TOKEN / ERROR / DONE`
- SSE Streaming
- Token Batching
- Vue Token 流式显示与 Agent Timeline
- `InMemorySaver` Checkpoint
- `threadId` 多轮上下文与会话隔离
- Docker Compose

## 目录

```text
backend/   FastAPI + LangGraph Agent Runtime
frontend/  Vue3 展示端
docs/      学习说明
```

## 1. 配置模型

复制根目录 `.env.example` 为 `.env`：

```env
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=你的KEY
LLM_MODEL=gpt-4o-mini
```

DeepSeek、Ollama 或其他 OpenAI-compatible 接口只需修改这三个变量。Ollama 常见配置示例：

```env
LLM_BASE_URL=http://host.docker.internal:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=qwen3:8b
```

模型必须支持 Tool Calling。

## 2. 本地启动后端

推荐 Python 3.11。

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
# source .venv/bin/activate
pip install -r requirements.txt
```

将 `backend/.env.example` 复制为 `backend/.env`，或直接设置系统环境变量，然后：

```bash
uvicorn wms_agent.application:app --reload --port 8000
```

Swagger：`http://localhost:8000/docs`

## 3. 本地启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`。

## 4. Docker Compose 一键启动

根目录创建 `.env` 后：

```bash
docker compose up -d --build
```

访问：

- Vue：`http://localhost:8080`
- FastAPI Swagger：`http://localhost:8000/docs`

## 5. curl 验证 SSE

Linux/macOS：

```bash
curl -N -X POST http://localhost:8000/api/agent/chat/unified-stream \
  -H 'Content-Type: application/json' \
  -d '{"message":"查询 MAT001 的库存、库存明细和库位","threadId":"wms-demo-001"}'
```

Windows PowerShell：

```powershell
@'
{
  "message": "查询 MAT001 的库存、库存明细和库位",
  "threadId": "wms-demo-001"
}
'@ | Set-Content -Encoding utf8 body.json

curl.exe -N -X POST "http://localhost:8000/api/agent/chat/unified-stream" `
  -H "Content-Type: application/json" `
  --data-binary "@body.json"
```

预期事件：`START -> STATUS -> TOOL_START... -> TOOL_END... -> STATUS -> TOKEN... -> DONE`。

## 6. Checkpoint 学习实验

保持 Python 进程不重启。

第一次使用同一个 `threadId`：

```json
{"message":"查询 MAT001 的库存","threadId":"checkpoint-demo"}
```

第二次：

```json
{"message":"那它在哪个库位？","threadId":"checkpoint-demo"}
```

目标：模型结合已有消息理解“它”指 MAT001，并调用 `query_location`。

再换成新 `threadId`：

```json
{"message":"那它在哪个库位？","threadId":"another-thread"}
```

该会话不应该共享前一个 Thread 的历史状态。

## 7. Mock WMS 数据

内置 `MAT001`、`MAT002`。为了直观看并行 Tool：

- `query_stock` 模拟约 2 秒
- `query_inventory_detail` 模拟约 50ms
- `query_location` 模拟约 2 秒

Timeline 应显示各自独立 Runtime 耗时，而不是三个相同时间。

## 8. 测试

安装依赖后：

```bash
cd backend
pytest -q
```

前端：

```bash
cd frontend
npm test
npm run build
```

## 9. 安全边界

当前只提供查询 Tool。未来 WMS 写操作不得让 LLM 直接操作数据库；必须通过受控业务 API，执行权限、参数、库存、状态机、幂等和事务校验，高风险操作需 Human-in-the-loop。

## 10. 下一阶段

建议按顺序扩展：

1. PostgreSQL Checkpointer
2. Session / Thread 管理
3. 短期与长期 Memory
4. WMS SOP / 设备手册 RAG
5. Workflow
6. Human-in-the-loop
7. Retry / Timeout / Idempotency
8. Evaluation / Trace / Metrics
# AI-Agent-demo
