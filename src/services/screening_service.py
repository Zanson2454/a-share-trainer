"""选股服务 — 五维评分筛选"""

from ..data.akshare_client import AKShareClient
from ..scorer import StockScore, FundamentalScorer, MarketEnvScorer, TechnicalScorer


def _score_market_env() -> tuple[float, str]:
    """用上证指数估算大盘环境；失败时返回中性分"""
    index_df = AKShareClient.get_index_data("000001")
    if index_df is None or index_df.empty:
        return 10.0, "大盘数据待确认"

    latest = index_df.iloc[-1]
    prev_close = index_df.iloc[-2]["close"] if len(index_df) > 1 else latest["close"]
    index_change = (latest["close"] - prev_close) / prev_close * 100 if prev_close else 0
    avg_volume = index_df["volume"].tail(20).mean()
    volume_ratio = latest["volume"] / avg_volume if avg_volume else 1
    trend = MarketEnvScorer.classify_market({
        "price_above_ma20": latest["close"] > index_df["close"].tail(20).mean(),
        "price_above_ma60": latest["close"] > index_df["close"].tail(60).mean(),
    })
    return MarketEnvScorer.score(index_change, volume_ratio, trend), trend


def screen_stocks(codes: list[str] | None = None) -> dict:
    """五维评分筛选候选股"""
    result: dict = {
        "market_score": 10.0,
        "market_trend": "震荡",
        "candidates": [],
        "pool_source": "",
        "total_in_pool": 0,
        "error": None,
    }

    if not AKShareClient.check_available():
        result["error"] = "AKShare 未安装，无法获取实时行情"
        return result

    try:
        sectors = AKShareClient.get_hot_sectors()
        sector_names = [s.get("name", "") for s in sectors] if sectors else []
        policy_score = 15 if sectors else 5
        policy_desc = "热点板块: " + "、".join(sector_names[:3]) if sector_names else "板块/政策数据待人工确认"
        market_score, market_trend = _score_market_env()
        result["market_score"] = market_score
        result["market_trend"] = market_trend

        # 候选池
        hot_codes = list(codes or [])
        pool_source = "用户指定"
        if not hot_codes:
            try:
                import akshare as ak
                spot_df = ak.stock_zh_a_spot_em()
                if spot_df is not None and not spot_df.empty:
                    top = spot_df.nlargest(20, "涨跌幅")
                    hot_codes = top["代码"].head(10).tolist()
                    pool_source = "实时行情（涨幅榜前10）"
                else:
                    result["error"] = "无法获取实时行情数据"
                    return result
            except Exception as e:
                result["error"] = f"获取实时行情失败: {e}"
                return result

        result["pool_source"] = pool_source

        for code in hot_codes:
            stock = StockScore(code=code)
            kline = AKShareClient.get_daily_kline(code)
            if kline is None or kline.empty:
                continue

            kline["ma5"] = kline["close"].rolling(5).mean()
            kline["ma20"] = kline["close"].rolling(20).mean()
            kline["ma60"] = kline["close"].rolling(60).mean()

            tech = TechnicalScorer.score(kline)
            stock.technical = tech["score"]
            stock.technical_desc = tech["desc"]

            stock.market_env = market_score
            fin = AKShareClient.get_financial_data(code)
            stock.name = fin.get("_name", "") or stock.name
            fund = FundamentalScorer.score(fin)
            stock.fundamental = fund["score"]
            stock.fundamental_desc = fund["desc"]

            stock.policy_hot = policy_score
            stock.policy_desc = policy_desc
            stock.risk_control = 8

            stock.reasons = [
                "大盘环境: " + market_trend,
                "技术面: " + stock.technical_desc,
                "基本面: " + stock.fundamental_desc,
            ]
            stock.risk_points = ["市场系统性风险", "个股流动性风险"]
            stock.counter_conditions = ["大盘转防守时重新评估", "跌破60日线时重新评估"]
            stock.confirm_questions = [
                "该股票最近是否有大股东减持公告？",
                "同行业是否有更好的标的？",
                "政策/热点分是否有可靠事件和板块共振支撑？",
            ]

            if stock.in_pool:
                result["candidates"].append({
                    "code": stock.code,
                    "name": stock.name,
                    "industry": stock.industry,
                    "scores": {
                        "market_env": stock.market_env,
                        "policy_hot": stock.policy_hot,
                        "fundamental": stock.fundamental,
                        "technical": stock.technical,
                        "risk_control": stock.risk_control,
                    },
                    "total": round(stock.total, 1),
                    "in_pool": stock.in_pool,
                    "technical_desc": stock.technical_desc,
                    "fundamental_desc": stock.fundamental_desc,
                    "policy_desc": stock.policy_desc,
                    "reasons": stock.reasons,
                    "risk_points": stock.risk_points,
                    "counter_conditions": stock.counter_conditions,
                    "confirm_questions": stock.confirm_questions,
                })

        result["total_in_pool"] = len(result["candidates"])

    except Exception as e:
        result["error"] = str(e)

    return result
