"""策略管理 — 列表、详情、创建、更新、删除"""

from fastapi import APIRouter, HTTPException
from ...services.strategy_service import (
    list_strategies, get_strategy, create_strategy,
    update_strategy, delete_strategy, get_indicator_reference,
)
from ..models.requests import StrategyCreateRequest, StrategyUpdateRequest

router = APIRouter(tags=["strategy"])


@router.get("/api/strategies/indicators")
def indicator_reference():
    return get_indicator_reference()


@router.get("/api/strategies")
def strategy_list():
    strategies = list_strategies()
    return {"strategies": strategies, "count": len(strategies)}


@router.get("/api/strategies/{name}")
def strategy_detail(name: str):
    result = get_strategy(name)
    if result is None:
        raise HTTPException(status_code=404, detail=f"策略「{name}」不存在")
    return result


@router.post("/api/strategies")
def strategy_create(body: StrategyCreateRequest):
    result = create_strategy(body.name)
    if result is None:
        raise HTTPException(status_code=400, detail="无效的策略名称")
    if result.get("error"):
        raise HTTPException(status_code=409, detail=result["error"])
    return result


@router.put("/api/strategies/{name}")
def strategy_update(name: str, body: StrategyUpdateRequest):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    result = update_strategy(name, updates)
    if result is None:
        raise HTTPException(status_code=404, detail=f"策略「{name}」不存在")
    return result


@router.delete("/api/strategies/{name}")
def strategy_delete(name: str):
    ok = delete_strategy(name)
    if not ok:
        raise HTTPException(status_code=404, detail=f"策略「{name}」不存在")
    return {"deleted": True, "name": name}
