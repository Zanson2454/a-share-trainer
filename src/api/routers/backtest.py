"""POST /api/backtest — 策略历史回测；GET /api/backtest/params — 参数定义"""

from fastapi import APIRouter, HTTPException
from ...services.backtest_service import run_backtest, get_default_params
from ..models.requests import BacktestRequest
from ..models.responses import BacktestResponse

router = APIRouter(tags=["backtest"])


@router.get("/api/backtest/params")
def backtest_params():
    return get_default_params()


@router.post("/api/backtest", response_model=BacktestResponse)
def backtest(body: BacktestRequest):
    result = run_backtest(body.strategy_name, body.start_date, body.end_date,
                          body.code, body.custom_params)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
