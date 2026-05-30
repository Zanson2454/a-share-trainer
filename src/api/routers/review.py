"""每日复盘 + 操作复盘 CRUD"""

from fastapi import APIRouter, HTTPException, Body
from ...services.review_service import (
    get_review_template,
    list_operations, get_operation, create_operation,
    update_operation, delete_operation, get_operation_stats,
)
from ..models.responses import ReviewTemplateResponse

router = APIRouter(tags=["review"])


@router.get("/api/review/template", response_model=ReviewTemplateResponse)
def review_template():
    return get_review_template()


# ── 操作复盘 ──

@router.get("/api/review/operations/stats")
def operation_stats():
    return get_operation_stats()


@router.get("/api/review/operations")
def operation_list():
    ops = list_operations()
    return {"operations": ops, "count": len(ops)}


@router.get("/api/review/operations/{op_id}")
def operation_detail(op_id: str):
    op = get_operation(op_id)
    if op is None:
        raise HTTPException(status_code=404, detail="操作记录不存在")
    return op


@router.post("/api/review/operations")
def operation_create(data: dict = Body(...)):
    return create_operation(data)


@router.put("/api/review/operations/{op_id}")
def operation_update(op_id: str, data: dict = Body(...)):
    result = update_operation(op_id, data)
    if result is None:
        raise HTTPException(status_code=404, detail="操作记录不存在")
    return result


@router.delete("/api/review/operations/{op_id}")
def operation_delete(op_id: str):
    ok = delete_operation(op_id)
    if not ok:
        raise HTTPException(status_code=404, detail="操作记录不存在")
    return {"deleted": True, "id": op_id}
