from fastapi import APIRouter
from .chat_controller import router as chat_router
from .agent_stream_router import router as stream_router
from .freeze_inventory_controller import router as freeze_router

router = APIRouter()
router.include_router(chat_router)
router.include_router(stream_router)
router.include_router(freeze_router)
