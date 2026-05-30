"""
GET /api/stocks/{code}/agent — AI Agent 股票深度研判
"""

from fastapi import APIRouter, HTTPException, Query
from ...services.agent_service import analyze_with_agents
from ..models.responses import AgentAnalysisResponse

router = APIRouter(tags=["agent-analysis"])


@router.get("/api/stocks/{code}/agent", response_model=AgentAnalysisResponse)
def agent_analysis(
    code: str,
    deep: bool = Query(False, description="是否使用深度模式（Pro 模型 + 5 轮辩论）"),
):
    """
    AI 多 Agent 深度分析一只股票

    4 个 AI 分析师并行分析 → 多空辩论 → PM 决策
    """
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(
            status_code=400,
            detail=f"无效的股票代码: {code}，请输入6位数字"
        )

    result = analyze_with_agents(code, deep=deep)

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return result
