# 后端架构与运行

业务应用和外部系统分开组织：`apps/warehouse` 拥有仓储规则、Agent、审批流程及 HTTP 接口；`integrations/wms` 负责 WMS HTTP 通信；`infrastructure` 管理模型、审计连接池和 checkpoint。

## 从哪里开始阅读

1. `wms_agent/application.py`：FastAPI 工厂，只配置生命周期、中间件和路由。
2. `wms_agent/bootstrap.py`：跨模块组合根，按依赖顺序创建资源并在退出时释放。
3. `wms_agent/apps/warehouse/container.py`：仓储应用的内部装配。
4. `wms_agent/apps/warehouse/workflows/freeze_inventory/service.py`：API 与 Agent 共用的冻结流程入口。
5. `wms_agent/apps/warehouse/ports`：业务需要的库存和库位能力协议。
6. `wms_agent/integrations/wms`：上述协议的实际 HTTP 实现。

## 依赖规则

- 仓储业务代码只依赖 ports 和应用模型，不导入具体 WMS Client。
- WMS Client 可以引用仓储 ports/models，不引用业务 Service、API 或 container。
- 公共基础设施不导入业务应用。
- 创建资源的上下文负责关闭；普通 service 只借用资源。
- Controller 通过 dependencies.py 获取应用服务，不持有模块全局服务变量。
- 保留两种历史事件模型供已有工具相关代码使用；当前流式 API 统一使用 agent/events，旧 unified-stream URL 作为该协议的弃用别名。

## 本地运行

要求 Python 3.11 或更高版本。在 backend 目录执行：

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m wms_agent.run
```

已有 `.env` 时不要覆盖，补齐 `CHECKPOINT_DB_URI` 和 WMS 配置即可。Windows 入口使用 SelectorEventLoop；Linux 也可使用 `uvicorn wms_agent.application:app`。

启动前，在审计数据库执行 `sql/001_approval_audit.sql`。`AUDIT_DB_URI` 留空时使用 checkpoint 数据库地址，但审计持有独立连接池。Checkpoint 表由 AsyncPostgresSaver.setup 初始化；生产环境可以将此初始化纳入部署步骤。

环境配置沿用 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`、`CORS_ORIGINS`，新增/明确 `CHECKPOINT_DB_URI`、`AUDIT_DB_URI`、`WMS_SERVICE_BASE_URL`、`WMS_SERVICE_TIMEOUT`。配置示例不含真实凭据。

Docker Compose 使用宿主机的外部数据库/WMS，不自动创建它们。Compose 变量来自项目根目录 `.env` 或启动环境；容器内不能使用 localhost 指代宿主机服务。

## 接口与状态

- POST `/api/agent/chat`、`/api/agent/chat/stream`
- POST `/api/agent/chat/unified-stream`：保留 URL，使用与 stream 相同的事件协议，标记弃用。
- POST `/api/workflow/freeze/start`、`/api/workflow/freeze/resume`
- GET `/api/agent/checkpoint/{thread_id}` 及 `/history`：调试用途。

会话请求支持 conversationId，并兼容旧 threadId 别名；返回会话字段统一为 conversationId。冻结接口 threadId 仍代表业务流程实例，不能与会话 ID 混用。每次流式请求与图内事件共用一个 requestId。

迁移保留图节点名、主要状态字段与 `FREEZE_INVENTORY:{thread_id}` 幂等键。审计和外部 WMS 写操作不构成跨系统原子事务，最终库存幂等仍由 WMS 保证。多进程下同实例并发调用需要调用方串行化或后续引入跨进程锁；当前不是分布式调度器。

## 测试

在项目根目录：

```powershell
python -m pytest -q
python -m compileall -q backend/wms_agent
```

测试使用内存 checkpoint、模型替身和 httpx.MockTransport，不连接真实服务。HTTP 测试通过 `create_app(Settings(), runtime_factory=...)` 替换运行时，确保不会因 lifespan 访问外部数据库。真实 PostgreSQL 重启恢复及 WMS/LLM 联调需另行执行。

## 后续接入 ERP

仅需要 ERP 查询能力时新增 integrations/erp，由 bootstrap 创建后注入需要该能力的业务应用；不复制 API、Agent 或工作流。需要独立采购业务时才增加 apps/procurement。多个应用共享同一外部接口而业务模型不同时，再拆独立响应模型与应用适配器。
