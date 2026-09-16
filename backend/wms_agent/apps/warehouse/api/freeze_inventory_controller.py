from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .dependencies import get_freeze_service
from wms_agent.apps.warehouse.workflows.freeze_inventory.service import FreezeWorkflowService

router = APIRouter(prefix="/api/workflow/freeze", tags=["Warehouse Freeze Workflow"])


class FreezeInventoryStartRequest(BaseModel):
    threadId: str = Field(min_length=1)
    materialCode: str = Field(min_length=1)
    quantity: int = Field(gt=0)


class FreezeInventoryResumeRequest(BaseModel):
    threadId: str = Field(min_length=1)
    approved: bool
    approverId: str = Field(min_length=1, max_length=64)
    remark: str = Field(default="", max_length=1000)


@router.post("/start")
async def start_freeze_inventory(body: FreezeInventoryStartRequest,
                                 service: FreezeWorkflowService = Depends(get_freeze_service)):
    try:
        return await service.start(thread_id=body.threadId, material_code=body.materialCode, quantity=body.quantity)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/resume")
async def resume_freeze_inventory(body: FreezeInventoryResumeRequest,
                                  service: FreezeWorkflowService = Depends(get_freeze_service)):
    try:
        return await service.resume(thread_id=body.threadId, approved=body.approved,
                                    approver_id=body.approverId, remark=body.remark)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
