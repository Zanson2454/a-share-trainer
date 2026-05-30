"""GET /api/screening — 五维评分筛选；POST /api/screening/natural — 自然语言选股"""

from fastapi import APIRouter, Query
from ...services.screening_service import screen_stocks
from ...services.nl_screening_service import screen_by_natural_language
from ..models.responses import ScreeningResponse
from ..models.requests import NaturalScreeningRequest

router = APIRouter(tags=["screening"])


@router.get("/api/screening", response_model=ScreeningResponse)
def screening(codes: str | None = Query(None, description="候选股代码，逗号分隔，如 600519,000858")):
    code_list = [c.strip() for c in codes.split(",") if c.strip()] if codes else []
    result = screen_stocks(code_list if code_list else None)
    return result


@router.post("/api/screening/natural", response_model=ScreeningResponse)
def natural_screening(body: NaturalScreeningRequest):
    return screen_by_natural_language(body.query)
