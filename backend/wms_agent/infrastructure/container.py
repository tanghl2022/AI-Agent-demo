from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
import httpx
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from wms_agent.config import Settings


@dataclass(frozen=True, slots=True)
class InfrastructureContainer:
    chat_model: BaseChatModel
    checkpointer: BaseCheckpointSaver
    audit_pool: AsyncConnectionPool


@asynccontextmanager
async def create_infrastructure_container(settings: Settings) -> AsyncIterator[InfrastructureContainer]:
    """初始化失败和正常关闭均按相反顺序释放已经创建的资源。"""
    settings.validate_runtime()
    async with AsyncExitStack() as stack:
        audit_pool = AsyncConnectionPool(settings.audit_db_uri or settings.checkpoint_db_uri,
                                         min_size=1, max_size=10, open=False)
        # 在打开之前登记关闭动作，避免连接失败时遗留后台任务。
        stack.push_async_callback(audit_pool.close)
        await audit_pool.open(wait=True)
        checkpointer = await stack.enter_async_context(
            AsyncPostgresSaver.from_conn_string(settings.checkpoint_db_uri)
        )
        await checkpointer.setup()
        # 同步与异步模型客户端均由本模块管理，避免 SDK 隐式资源泄漏。
        sync_http = stack.enter_context(httpx.Client(timeout=60))
        async_http = await stack.enter_async_context(httpx.AsyncClient(timeout=60))
        model = ChatOpenAI(model=settings.llm_model, api_key=settings.llm_api_key,
                           base_url=settings.llm_base_url, http_client=sync_http,
                           http_async_client=async_http)
        yield InfrastructureContainer(model, checkpointer, audit_pool)
