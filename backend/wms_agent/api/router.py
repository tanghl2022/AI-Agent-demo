from fastapi import APIRouter
from .health import router as health_router
from wms_agent.apps.warehouse.api.router import router as warehouse_router

router = APIRouter()
router.include_router(health_router)
router.include_router(warehouse_router)
