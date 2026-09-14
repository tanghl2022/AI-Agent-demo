import asyncio
from contextlib import asynccontextmanager

from langchain_openai import ChatOpenAI
from psycopg import AsyncConnection
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from wms_agent.audit.approval_audit_repository import ApprovalAuditRepository
from wms_agent.audit.approval_audit_service import ApprovalAuditService
from wms_agent.api.chat_controller import router

from wms_agent.clients.java.wms_inventory_client import WmsInventoryClient
from wms_agent.clients.java.wms_location_client import WmsLocationClient
from wms_agent.clients.contracts import InventoryClient, LocationClient
from wms_agent.config import settings
from wms_agent.graphs.agent_main_graph_factory import build_agent_main_graph
from wms_agent.graphs.freeze_inventory_workflow import (
    build_freeze_inventory_workflow,
)
from wms_agent.services.agent_service import AgentService
from wms_agent.services.freeze_execution_service import FreezeExecutionService
from wms_agent.services.wms_query_service import WmsQueryService
from wms_agent.api.freeze_inventory_controller import (
    router as freeze_inventory_router,
)
from wms_agent.api.agent_stream_router import (
    router as agent_stream_router,
)

@asynccontextmanager
async def lifespan(
    app: FastAPI
):
    print(
        "当前 EventLoop:",
        asyncio.get_running_loop().__class__.__name__
    )
    """
    FastAPI 应用生命周期。

    启动：
    1. 创建 PostgreSQL Checkpointer
    2. 初始化 LangGraph Checkpoint 表
    3. 创建 Tool
    4. 编译 Graph
    5. 创建 AgentService

    关闭：
    自动释放 PostgreSQL Checkpointer 资源。
    """

    # ========================================
    # 1. 创建 PostgreSQL Checkpointer
    # ========================================

    # ========================================
    # 创建异步 PostgreSQL Checkpointer
    # ========================================

    async with AsyncPostgresSaver.from_conn_string(
            settings.checkpoint_db_uri
    ) as checkpointer:
        audit_connection = await AsyncConnection.connect(
            settings.checkpoint_db_uri
        )
        # ====================================
        # 2. 初始化 LangGraph Checkpoint 表
        #
        # 第一次必须执行。
        # 重复执行也是允许的。
        # ====================================

        await checkpointer.setup()

        chat_model = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key or "not-configured",
            base_url=settings.llm_base_url,
            temperature=0,
            extra_body={
                "thinking": {
                    "type": "disabled"
                }
            }
        )


        wms_inventory_client = app.state.inventory_client or WmsInventoryClient(
            base_url=settings.wms_service_base_url,
            timeout=settings.wms_service_timeout,
        )

        location_query_client = app.state.location_client or WmsLocationClient(
            base_url=settings.wms_service_base_url,
            timeout=settings.wms_service_timeout,
        )

        query_service = WmsQueryService(
            wms_inventory_client, location_query_client
        )

        audit_repository = (
            ApprovalAuditRepository(
                audit_connection
            )
        )

        audit_service = (
            ApprovalAuditService(
                audit_repository
            )
        )

        # freeze_execution_service = FreezeExecutionService(audit_connection)

        freeze_execution_service = (
            FreezeExecutionService(
                wms_inventory_client
            )
        )

        freeze_inventory_workflow = (
            build_freeze_inventory_workflow(
                query_service=query_service,
                audit_service=audit_service,
                checkpointer=checkpointer,
                freeze_execution_service=freeze_execution_service,
            )
        )

        app.state.freeze_inventory_workflow = (
            freeze_inventory_workflow
        )

        graph = build_agent_main_graph(
            chat_model,
            wms_inventory_client,
            location_query_client,
            freeze_inventory_workflow,
            checkpointer,
        )

        app.state.agent_service = AgentService(
            graph
        )

        # FastAPI 正常运行
        yield

        await audit_connection.close()


def create_app(
    *,
    inventory_client: InventoryClient | None = None,
    location_client: LocationClient | None = None,
) -> FastAPI:

    app = FastAPI(
        title="WMS Agent Demo",
        version="1.0.0",
        lifespan=lifespan,
    )

    # 未注入时使用 Java；演示和测试显式注入模拟客户端。
    app.state.inventory_client = inventory_client
    app.state.location_client = location_client

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(
            settings.cors_origins
        ),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(
        router
    )
    app.include_router(
        freeze_inventory_router
    )
    app.include_router(
        agent_stream_router
    )
    return app


app = create_app()
