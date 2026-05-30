"""GET /api/learn/daily — 每日学习主题"""

from fastapi import APIRouter
from ...services.learning_service import get_daily_learning
from ..models.responses import LearningResponse

router = APIRouter(tags=["learning"])


@router.get("/api/learn/daily", response_model=LearningResponse)
def daily_learning():
    return get_daily_learning()
