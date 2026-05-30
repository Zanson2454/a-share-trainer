"""GET /api/premarket — 盘前环境分析"""

from fastapi import APIRouter
from ...services.premarket_service import get_premarket_analysis, check_dow_confirmation
from ..models.responses import PremarketResponse

router = APIRouter(tags=["premarket"])


@router.get("/api/premarket", response_model=PremarketResponse)
def premarket_analysis():
    return get_premarket_analysis()
