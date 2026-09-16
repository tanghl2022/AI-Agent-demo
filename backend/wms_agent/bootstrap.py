"""唯一的跨模块组合根：技术资源 → 外部系统 → 业务应用。"""
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from wms_agent.config import Settings
from wms_agent.infrastructure.container import create_infrastructure_container
from wms_agent.integrations.wms.container import create_wms_integration
from wms_agent.apps.warehouse.container import WarehouseContainer, create_warehouse_container
from wms_agent.apps.warehouse.audit.approval_audit_repository import ApprovalAuditRepository
from wms_agent.apps.warehouse.audit.approval_audit_service import ApprovalAuditService


@dataclass(frozen=True, slots=True)
class ApplicationRuntime:
    warehouse: WarehouseContainer


@asynccontextmanager
async def create_runtime(settings: Settings) -> AsyncIterator[ApplicationRuntime]:
    async with AsyncExitStack() as stack:
        infrastructure = await stack.enter_async_context(create_infrastructure_container(settings))
        wms = await stack.enter_async_context(create_wms_integration(settings.wms))
        audit = ApprovalAuditService(ApprovalAuditRepository(infrastructure.audit_pool))
        warehouse = create_warehouse_container(
            inventory_client=wms.inventory_client, location_client=wms.location_client,
            chat_model=infrastructure.chat_model, checkpointer=infrastructure.checkpointer, audit_service=audit,
        )
        yield ApplicationRuntime(warehouse)


RuntimeFactory = Callable[[Settings], AbstractAsyncContextManager[ApplicationRuntime]]


def create_lifespan(settings: Settings, runtime_factory: RuntimeFactory):
    @asynccontextmanager
    async def lifespan(app):
        async with runtime_factory(settings) as runtime:
            app.state.runtime = runtime
            try:
                yield
            finally:
                del app.state.runtime
    return lifespan
