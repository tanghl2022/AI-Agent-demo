from fastapi import APIRouter

router = APIRouter()


@router.get("/api/health")
async def health():
    """进程健康检查；真实资源初始化失败会阻止应用启动。"""
    return {"status": "ok", "service": "wms-agent-demo"}
