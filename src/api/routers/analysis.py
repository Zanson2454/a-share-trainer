"""GET /api/stocks/{code}/analysis — 个股深度分析；GET /api/stocks/search — 股票搜索；GET /api/stocks/{code}/patterns — K线形态识别"""

from fastapi import APIRouter, HTTPException, Query
from ...services.analysis_service import analyze_stock
from ...services.pattern_recognition import detect_patterns
from ...data.akshare_client import AKShareClient
from ..models.responses import StockAnalysisResponse, PatternResponse

router = APIRouter(tags=["stock-analysis"])


@router.get("/api/stocks/search")
def search_stocks(q: str = Query(..., min_length=1, description="名称或代码关键词")):
    results = AKShareClient.search_stocks(q)
    return {"keyword": q, "results": results, "count": len(results)}


@router.get("/api/stocks/{code}/analysis", response_model=StockAnalysisResponse)
def stock_analysis(code: str):
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(status_code=400, detail=f"无效的股票代码: {code}，请输入6位数字")
    result = analyze_stock(code)
    if result is None:
        raise HTTPException(status_code=404, detail=f"无法获取 {code} 的数据")
    return result


PERIOD_LABELS: dict[str, str] = {
    "daily": "日线", "weekly": "周线", "monthly": "月线",
    "60": "60分钟", "30": "30分钟", "15": "15分钟",
    "120": "120分钟", "4h": "4小时",
}


@router.get("/api/stocks/{code}/patterns", response_model=PatternResponse)
def stock_patterns(
    code: str,
    period: str = Query("daily", description="K线周期: daily/weekly/monthly/4h/120/60/30/15"),
):
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(status_code=400, detail=f"无效的股票代码: {code}")

    valid_periods = {"daily", "weekly", "monthly", "4h", "120", "60", "30", "15"}
    if period not in valid_periods:
        raise HTTPException(status_code=400, detail=f"无效周期: {period}，可选: {', '.join(sorted(valid_periods))}")

    kline = AKShareClient.get_kline_for_period(code, period)
    if kline is None or kline.empty:
        raise HTTPException(status_code=404, detail=f"无法获取 {code} 的{PERIOD_LABELS.get(period, period)}K线数据")

    patterns = detect_patterns(kline)

    first_date = str(kline["date"].iloc[0])[:10]
    last_date = str(kline["date"].iloc[-1])[:10]

    # 获取股票名称
    name = ""
    fin = AKShareClient.get_financial_data(code)
    if fin:
        name = fin.get("_name", "")

    return {
        "code": code,
        "name": name,
        "period": period,
        "patterns": patterns,
        "data_range": f"{first_date} ~ {last_date}",
    }
