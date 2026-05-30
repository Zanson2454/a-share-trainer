"""Pydantic request models for API endpoints."""

from datetime import date
from pydantic import BaseModel, Field


class BacktestRequest(BaseModel):
    strategy_name: str = Field(..., description="策略名称，如 均线金叉 / L0-纯金叉死叉")
    start_date: str = Field(..., description="开始日期 YYYYMMDD")
    end_date: str = Field(..., description="结束日期 YYYYMMDD")
    code: str = Field(default="000300", description="回测标的代码")
    custom_params: dict | None = Field(default=None, description="自定义12参数，覆盖默认值")

class ScreeningRequest(BaseModel):
    codes: list[str] = Field(default=[], description="指定候选股代码，为空则自动获取涨幅榜前10")

class ObsidianSyncRequest(BaseModel):
    target: str = Field(..., description="同步目标: learning / analysis / review / strategy / backtest")
    code: str | None = None
    name: str | None = None

class NaturalScreeningRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200, description="自然语言选股查询，如 高ROE低PE的白酒股")

class StrategyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)

class StrategyUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    entry_conditions: list[dict] | None = None
    exit_conditions: list[dict] | None = None
    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None
    position_pct: float | None = None
    status: str | None = None
    market_env: list[str] | None = None
    notes: str | None = None
